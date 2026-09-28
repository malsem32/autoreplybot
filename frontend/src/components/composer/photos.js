/** API photo URLs → picker items. The backend accepts the URL back as a ref. */
export function photosFromUrls(urls = []) {
  return urls.map((url) => ({ ref: url, url }));
}

export function photoRefs(photos) {
  return photos.map((p) => p.ref);
}
