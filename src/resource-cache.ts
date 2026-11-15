// Session-memory only: no records or authorization decisions persist to disk.
export function createResourceCache<T>(
  fetcher: (path: string) => Promise<T>,
  ttl = 30_000,
) {
  const values = new Map<string, { data: T; at: number }>();
  const pending = new Map<string, Promise<T>>();
  let generation = 0;
  return {
    peek(path: string) {
      return values.get(path)?.data;
    },
    clear(paths?: string[]) {
      generation++;
      if (paths) paths.forEach((path) => values.delete(path));
      else values.clear();
      pending.clear();
    },
    async get(path: string) {
      const old = values.get(path);
      if (old && Date.now() - old.at < ttl) return old.data;
      if (pending.has(path)) return pending.get(path)!;
      const current = generation;
      const request = fetcher(path)
        .then((data) => {
          if (generation === current)
            values.set(path, { data, at: Date.now() });
          return data;
        })
        .finally(() => {
          if (generation === current) pending.delete(path);
        });
      pending.set(path, request);
      return request;
    },
  };
}
