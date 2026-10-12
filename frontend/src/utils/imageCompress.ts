/** 上传前压缩（ADR-20261012 图片篇 §4.7）：
 *  - 等比缩到 maxEdge、导出 JPEG（顺带把 iPhone HEIC 等解码后转成可上传格式）
 *  - 解码失败（极少数格式）时原样返回，交给服务端裁决（不在这里吞掉错误） */
export async function compressImage(
  file: File,
  maxEdge = 2000,
  quality = 0.85,
): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height))
    const width = Math.max(1, Math.round(bitmap.width * scale))
    const height = Math.max(1, Math.round(bitmap.height * scale))

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.drawImage(bitmap, 0, 0, width, height)
    bitmap.close()

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', quality),
    )
    if (!blob) return file
    const name = `${file.name.replace(/\.[^.]+$/, '') || 'image'}.jpg`
    return new File([blob], name, { type: 'image/jpeg' })
  } catch {
    return file
  }
}
