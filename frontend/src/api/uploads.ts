import { http } from './http'

export interface UploadResult {
  key: string
  url: string
  width: number
  height: number
  bytes: number
}

/** 上传图片（服务端统一校验 + 规范化 + 抹 EXIF；见 ADR-20261012 图片篇 §4.4）。
 *  返回值只保留 key 用于业务引用；URL 展示统一走 utils/media.ts */
export async function uploadImage(file: File): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await http.post('/uploads/images', form)
  return res.data
}
