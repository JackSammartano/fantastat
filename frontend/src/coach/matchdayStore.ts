import type { MatchdayImport } from "./types";

const DB_NAME = "fantalab-coach";
const STORE_NAME = "matchday-imports";

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE_NAME, { keyPath: "key" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function run<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, mode);
    const request = action(transaction.objectStore(STORE_NAME));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    transaction.oncomplete = () => database.close();
  });
}

export const matchdayStore = {
  list: () => run<MatchdayImport[]>("readonly", (store) => store.getAll()).then((rows) => rows.sort((a, b) => b.season.localeCompare(a.season) || b.matchday - a.matchday)),
  save: (value: MatchdayImport) => run<IDBValidKey>("readwrite", (store) => store.put(value)),
  remove: (key: string) => run<undefined>("readwrite", (store) => store.delete(key))
};
