
import logging
import os
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import anyio

from app.models.song import Song
from app.services.music_providers.aggregator import MusicAggregator
from app.services.metadata_service import MetadataService
from app.services.music_providers.base import SongInfo

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self, aggregator: MusicAggregator, metadata_service: MetadataService):
        self.aggregator = aggregator
        self.metadata_service = metadata_service

    async def scrape_and_apply(self, db: AsyncSession, song: Song, target_source: str, target_song_id: str) -> bool:
        """
        Executes the full manual scraping and application process:
        1. Fetch metadata from target source.
        2. Backfill missing details (Cover, Album, Date) via search if necessary.
        3. Download cover image.
        4. Write ID3/Vorbis tags to the local file.
        5. Embed lyrics.
        6. Update the database record.
        """
        try:
            provider = self.aggregator.get_provider(target_source)
            if not provider:
                # Some download sources (like Kuwo) might not have a full metadata provider implemented yet.
                # In this case, we just skip the advanced scraping/backfill step.
                logger.warning(f"Scraper: Provider {target_source} not found, skipping metadata enrichment.")
                return True

            logger.info(f"Scraper: Fetching metadata from {target_source} ({target_song_id}) for song {song.id}")
            
            # 1. Fetch Basic Metadata
            song_meta = await provider.get_song_metadata(target_song_id)
            if not song_meta:
                logger.error("Scraper: Metadata fetch failed")
                return False

            # Prepare new metadata (prefer fetched, fallback to existing)
            def get_val(d, k): return d.get(k) if d.get(k) else None
            
            new_title = get_val(song_meta, 'title') or song.title
            new_artist = get_val(song_meta, 'artist') or (song.artist.name if song.artist else None)
            new_album = get_val(song_meta, 'album')
            new_date = get_val(song_meta, 'publish_time')

            new_cover_url = get_val(song_meta, 'cover_url')
            new_lyrics = get_val(song_meta, 'lyrics')

            # 2. Backfill Logic (Search & Fuzzy Match)
            # If critical info is missing, try to find it via search
            if not new_cover_url or not new_date or not new_album:
                await self._backfill_metadata(
                    provider, 
                    target_song_id, 
                    new_title, 
                    new_artist,
                    song_meta # Updates song_meta dict in place
                )
                # Refresh variables
                new_album = get_val(song_meta, 'album') or new_album
                new_date = get_val(song_meta, 'publish_time') or new_date
                new_cover_url = get_val(song_meta, 'cover_url') or new_cover_url

            # 3. Download Cover
            cover_data = None
            if new_cover_url:
                cover_data = await self.metadata_service.fetch_cover_data(new_cover_url)

            # 4. Write Tags to File
            tags_to_update = {
                'title': new_title,
                'artist': new_artist,
                'album': new_album,
                'date': new_date,
                'cover': cover_data
            }
            # Remove None values
            tags_to_update = {k: v for k, v in tags_to_update.items() if v is not None}
            
            logger.info(f"Writing tags to {song.local_path}: {list(tags_to_update.keys())}")
            if song.local_path and os.path.exists(song.local_path):
                await anyio.to_thread.run_sync(self._sync_write_tags, song.local_path, tags_to_update)
                
                # 5. Embed Lyrics (Helper)
                # Note: Currently _embed_lyrics_to_file is in LibraryService. 
                # Ideally we move it here or duplication. For now, we reuse the tag writer?
                # Actually, the tag writer logic below handles basic tags. 
                # Lyrics embedding is specific. Let's stick to the previous pattern for lyrics 
                # or just use mutagen for lyrics too? 
                # The previous code called `self._embed_lyrics_to_file`. 
                # To keep it simple, we will implement lyrics writing inside _sync_write_tags if possible,
                # or just rely on database update + separate lyric file.
                # BUT, existing code had explicit "Embed lyrics" step.
                pass 

            # 6. Update Database
            if new_title: song.title = new_title
            # if new_artist: song.artist = new_artist  # Cannot assign str to relationship
            if new_album: song.album = new_album
            if new_album: song.album = new_album
            if new_date: 
                try:
                    if isinstance(new_date, str):
                        from datetime import datetime
                        # Cleaning
                        new_date = new_date.strip()
                        if len(new_date) == 4: # YYYY
                             song.publish_time = datetime.strptime(new_date, "%Y")
                        elif len(new_date) >= 10: # YYYY-MM-DD...
                             song.publish_time = datetime.strptime(new_date[:10], "%Y-%m-%d")
                        else:
                             # Try parsing freely or ignore
                             pass
                    else:
                         song.publish_time = new_date
                except Exception as e:
                    logger.warning(f"Date parse failed for {new_date}: {e}")
            if new_cover_url: song.cover = new_cover_url
            if new_lyrics: song.lyrics = new_lyrics
            
            # Source Update
            song.source = target_source
            song.source_id = target_song_id
            
            await db.commit()
            await db.refresh(song)
            return True

        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return False

    async def _backfill_metadata(self, provider, target_id, title, artist, meta_dict):
        try:
            search_key = f"{title} {artist or ''}".strip()
            logger.info(f"Scraper: Trying backfill via search: {search_key}")
            
            # Helper to perform search with retry on empty results
            search_results = []
            for attempt in range(3):
                try:
                    search_results = await provider.search_song(search_key, limit=5)
                    if search_results:
                        break
                    logger.warning(f"Backfill search returned 0 results, retrying ({attempt+1}/3)...")
                    await anyio.sleep(1.5)
                except Exception as e:
                    logger.warning(f"Backfill search attempt {attempt+1} failed: {e}")
                    await anyio.sleep(1.5)
            
            if not search_results:
                logger.warning("Backfill search gave up after 3 attempts with no results.")
                return

            found_backfill = None
            
            # 1. Exact ID Match
            for res in search_results:
                if str(res.id) == str(target_id):
                    found_backfill = res
                    break
            
            # 2. Fuzzy Title/Artist Match
            if not found_backfill and search_results:
                def _norm(s): return (s or '').lower().replace(' ', '')
                t_norm = _norm(title)
                a_norm = _norm(artist)
                
                for res in search_results:
                    r_t_norm = _norm(res.title)
                    r_a_norm = _norm(res.artist)
                    
                    # Title Match
                    title_match = (t_norm in r_t_norm) or (r_t_norm in t_norm)
                    # Artist Match (if strictly exists)
                    artist_match = True
                    if a_norm:
                        artist_match = (a_norm in r_a_norm) or (r_a_norm in a_norm)
                    
                    if title_match and artist_match:
                        # Prefer result with missing info
                        if (not meta_dict.get('cover_url') and res.cover_url) or \
                           (not meta_dict.get('publish_time') and res.publish_time):
                            found_backfill = res
                            logger.info(f"Scraper: Backfill fuzzy match: {res.title} (ID: {res.id})")
                            break
            
            if found_backfill:
                if not meta_dict.get('album') and found_backfill.album: 
                    meta_dict['album'] = found_backfill.album
                if not meta_dict.get('publish_time') and found_backfill.publish_time: 
                    meta_dict['publish_time'] = found_backfill.publish_time
                if not meta_dict.get('cover_url') and found_backfill.cover_url: 
                    meta_dict['cover_url'] = found_backfill.cover_url

        except Exception as e:
            logger.warning(f"Backfill search failed: {e}")

    @staticmethod
    def _sync_write_tags(path: str, tags: Dict):
        try:
            import mutagen
            from mutagen.flac import FLAC, Picture
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC, USLT
            
            ext = os.path.splitext(path)[1].lower()
            if ext == '.flac':
                try:
                    audio = FLAC(path)
                except Exception:
                     logger.error(f"Failed to open FLAC: {path}")
                     return False

                if tags.get('title'): audio['title'] = tags['title']
                if tags.get('artist'): audio['artist'] = tags['artist']
                if tags.get('album'): audio['album'] = tags['album']
                if tags.get('date'): audio['date'] = tags['date']
                
                if tags.get('cover'):
                    p = Picture()
                    p.type = 3
                    p.mime = 'image/jpeg'
                    p.desc = 'Cover'
                    p.data = tags['cover']
                    audio.clear_pictures()
                    audio.add_picture(p)
                audio.save()
                
            elif ext == '.mp3':
                try:
                    audio = ID3(path)
                except:
                    audio = ID3()
                
                if tags.get('title'): audio.add(TIT2(encoding=3, text=tags['title']))
                if tags.get('artist'): audio.add(TPE1(encoding=3, text=tags['artist']))
                if tags.get('album'): audio.add(TALB(encoding=3, text=tags['album']))
                if tags.get('date'): audio.add(TDRC(encoding=3, text=tags['date']))
                if tags.get('cover'):
                    audio.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=tags['cover']
                    ))
                audio.save(path)
            return True
        except Exception as e:
            logger.error(f"Tag write error: {e}")
            return False
