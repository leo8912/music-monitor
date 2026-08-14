/**
 * 音质判定统一入口 (M4)
 *
 * 此前音质阈值分散在 SongList (>=900) / DownloadList (>=1000) /
 * MetadataMatcher (>=999) 三处且互相矛盾, 同一 FLAC 文件在不同组件
 * 会显示 SQ / FLAC / 普通 等不同标签。统一规则 (以网易云 br 数值为准):
 *
 *   br >= 2000  → HR  (Hi-Res, 24bit/96kHz+, 码率远超 320kbps)
 *   br >= 900   → SQ  (FLAC 无损, 网易云 FLAC 典型 br=999)
 *   br >= 320   → HQ  (320kbps MP3)
 *   br >= 192   → PQ  (192kbps)
 *   其他        → PQ  (128kbps 及以下)
 */

/** 码率 (kbps, 网易云 br 数值) → 音质等级标签 */
export function bitrateToQuality(br: number): 'HR' | 'SQ' | 'HQ' | 'PQ' {
    if (br >= 2000) return 'HR'
    if (br >= 900) return 'SQ'
    if (br >= 320) return 'HQ'
    return 'PQ'
}

/** 码率 → 展示文案 (FLAC / 320K / 192K / 128K 等) */
export function bitrateToQualityLabel(br: number): string {
    if (br >= 2000) return 'HR'
    if (br >= 900) return 'FLAC'
    if (br >= 320) return '320K'
    if (br >= 192) return '192K'
    if (br >= 128) return '128K'
    return `${br}K`
}

/** 兼容入参可能是字符串 ("999" / "FLAC" / "SQ") 的调用方 */
export function qualityLabelOf(value: unknown): string {
    if (value === null || value === undefined || value === '') return ''
    const s = String(value)
    if (s.match(/^(SQ|HQ|HR|PQ)$/i)) return s.toUpperCase()
    const q = parseInt(s, 10)
    if (!isNaN(q)) return bitrateToQualityLabel(q)
    return s
}
