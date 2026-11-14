export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export function validateImages(files: File[]) {
  if (files.length > 5)
    throw Error("Choose at most 5 images. No files were uploaded.");
  for (const file of files) {
    if (file.size > MAX_IMAGE_BYTES)
      throw Error(
        `“${file.name}” is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is 5 MB per image. Choose a smaller image. No files were uploaded.`,
      );
    if (file.size === 0)
      throw Error(`“${file.name}” is empty. Choose a valid image.`);
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
      throw Error(
        `“${file.name}” is not a supported image. Choose JPEG, PNG or WebP. SVG and other files are not accepted.`,
      );
  }
  if (files.reduce((n, f) => n + f.size, 0) > 25 * 1024 * 1024)
    throw Error("The total attachment limit is 25 MB.");
}
