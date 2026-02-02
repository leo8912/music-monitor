
import { get, post, del } from './index'

export interface ArtistAddRequest {
    name: string;
    source: string;
    artist_id: string;
    avatar?: string;
}

export interface MonitoredArtist {
    id: number;
    name: string;
    source_count: number;
    sources: any[];
    is_monitored: boolean;
}

export const getMonitoredArtists = (): Promise<MonitoredArtist[]> => {
    return get('/api/subscription/artists')
}

export const addArtist = (data: ArtistAddRequest): Promise<{ success: boolean; message: string }> => {
    return post('/api/subscription/artists', data)
}

export const deleteArtist = (artistId: number): Promise<{ success: boolean; message: string }> => {
    return del(`/api/subscription/artists/${artistId}`)
}

export const getArtistDetail = (artistId: string | number): Promise<any> => {
    return get(`/api/subscription/artists/${artistId}`)
}
