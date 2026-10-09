import * as SparkMD5 from 'spark-md5';

// Runs outside the UI thread with 16 MiB slices for high-throughput client hashing
self.onmessage = async ({ data: file }: MessageEvent<File>) => {
  const hash = new SparkMD5.ArrayBuffer();
  try {
    const chunkSize = 16 * 1024 * 1024;
    let lastProgress = -1;
    for (let offset = 0; offset < file.size; offset += chunkSize) {
      hash.append(await file.slice(offset, offset + chunkSize).arrayBuffer());
      const currentProgress = Math.round((Math.min(offset + chunkSize, file.size) / file.size) * 100);
      if (currentProgress !== lastProgress) {
        lastProgress = currentProgress;
        self.postMessage({ progress: currentProgress });
      }
    }
    self.postMessage({ progress: 100, checksum: hash.end() });
  } catch {
    self.postMessage({ error: 'The selected file could not be read.' });
  } finally {
    hash.destroy();
  }
};
