    async def apply_metadata_match(self, db: AsyncSession, song_id: int, target_source: str, target_song_id: str):
        """
        手动应用元数据匹配 (Manual Match)
        """
        from app.models.song import Song
        import datetime
        
        logger.info(f"Manual Match: Fetching metadata from {target_source} ({target_song_id}) for song {song_id}")
        
        song = await db.get(Song, song_id)
        if not song:
            logger.error(f"Song not found: {song_id}")
            return False
            
        if not song.local_path or not os.path.exists(song.local_path):
             logger.error(f"Local file not found: {song.local_path}")
             return False
             
        # 1. Fetch Target Metadata
        metadata_service = MetadataService()
        provider = metadata_service._get_provider(target_source)
        if not provider:
             logger.error(f"Provider not found: {target_source}")
             return False
             
        try:
            # Most providers have get_song_metadata(id)
            song_meta = await provider.get_song_metadata(target_song_id)
            if not song_meta:
                 logger.error("Failed to fetch metadata from source")
                 return False
                 
            # 2. Prepare Data
            # Adapting the dict/object return from provider
            def get_val(obj, key):
                return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)

            new_title = get_val(song_meta, 'title') or song.title
            new_artist = get_val(song_meta, 'artist') 
            new_album = get_val(song_meta, 'album')
            new_date = get_val(song_meta, 'publish_time')
            new_cover_url = get_val(song_meta, 'cover_url')
            new_lyrics = get_val(song_meta, 'lyrics')
            
            # 3. Download Cover if exists
            cover_data = None
            if new_cover_url:
                 cover_data = await metadata_service.fetch_cover_data(new_cover_url)
                 
            # 4. Force Write to File (Overwrite mode)
            tags_to_update = {
                'title': new_title,
                'album': new_album,
            }
            # Only update artist if present to avoid wiping
            if new_artist:
                tags_to_update['artist'] = new_artist
                
            if cover_data: tags_to_update['cover'] = cover_data
            
            if new_date: 
                 # Date formatting
                 if isinstance(new_date, datetime.datetime):
                     tags_to_update['date'] = new_date.strftime('%Y-%m-%d')
                 else:
                     tags_to_update['date'] = str(new_date)[:10]

            logger.info(f"Writing tags to {song.local_path}: {tags_to_update.keys()}")
            await metadata_service.param_write_to_file(song.local_path, tags_to_update)
            
            # Embed lyrics if available
            if new_lyrics:
                await self._embed_lyrics_to_file(song.local_path, new_lyrics)
            
            # 5. Update DB
            song.title = new_title
            song.album = new_album
            song.cover = new_cover_url
            if new_date:
                try:
                    pt_str = str(new_date)
                    if len(pt_str) == 4:
                        song.publish_time = datetime.datetime.strptime(pt_str, "%Y")
                    elif len(pt_str) >= 10:
                        song.publish_time = datetime.datetime.strptime(pt_str[:10], "%Y-%m-%d")
                except: pass
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Apply Match Failed: {e}", exc_info=True)
            return False
