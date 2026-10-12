/** 媒体 key → URL 的唯一映射（见 .deepcode/ADR-20261012-Waynote-image-upload.md §4.2）。
 *  数据库只存相对 key（内容与位置分离）；将来换 COS/CDN 只改这里的前缀。 */

const MEDIA_PREFIX = '/media'

export function mediaUrl(key: string | null | undefined): string | undefined {
  return key ? `${MEDIA_PREFIX}/${key}` : undefined
}

/** 缩略图由主图 key 推导（{stem}.thumb.jpg，不变量 I2；数据库不存缩略图 key） */
export function thumbUrl(key: string | null | undefined): string | undefined {
  return key ? `${MEDIA_PREFIX}/${key.replace(/\.jpg$/, '.thumb.jpg')}` : undefined
}
