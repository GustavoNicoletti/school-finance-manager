import { api } from "./api";
import { Guardian, RolePermissionMatrix, Student, User } from "../types";

type CacheEntry<T> = {
  expiresAt: number;
  value?: T;
  promise?: Promise<T>;
};

const LOOKUP_TTL_MS = 5 * 60 * 1000;

const cache = new Map<string, CacheEntry<unknown>>();

function readCache<T>(key: string) {
  const now = Date.now();
  const entry = cache.get(key) as CacheEntry<T> | undefined;
  if (!entry) {
    return null;
  }
  if (entry.value !== undefined && entry.expiresAt > now) {
    return entry.value;
  }
  if (entry.promise) {
    return entry.promise;
  }
  cache.delete(key);
  return null;
}

async function rememberLookup<T>(key: string, loader: () => Promise<T>): Promise<T> {
  const cached = readCache<T>(key);
  if (cached instanceof Promise) {
    return cached;
  }
  if (cached !== null) {
    return cached;
  }

  const promise = loader()
    .then((value) => {
      cache.set(key, {
        value,
        expiresAt: Date.now() + LOOKUP_TTL_MS,
      });
      return value;
    })
    .catch((error) => {
      cache.delete(key);
      throw error;
    });

  cache.set(key, {
    expiresAt: Date.now() + LOOKUP_TTL_MS,
    promise,
  });

  return promise;
}

export async function getCachedStudents() {
  return rememberLookup<Student[]>("students:all", async () => {
    const { data } = await api.get<Student[]>("/students", { params: { limit: 500 } });
    return data;
  });
}

export async function getCachedGuardians() {
  return rememberLookup<Guardian[]>("guardians:all", async () => {
    const { data } = await api.get<Guardian[]>("/guardians", { params: { limit: 500 } });
    return data;
  });
}

export async function getCachedUsers() {
  return rememberLookup<User[]>("users:all", async () => {
    const { data } = await api.get<User[]>("/users", { params: { limit: 500 } });
    return data;
  });
}

export async function getCachedRolePermissionMatrix() {
  return rememberLookup<RolePermissionMatrix>("role-permissions:matrix", async () => {
    const { data } = await api.get<RolePermissionMatrix>("/role-permissions");
    return data;
  });
}

export function invalidateLookup(key: "students" | "guardians" | "users" | "role-permissions") {
  const keys = {
    students: ["students:all"],
    guardians: ["guardians:all"],
    users: ["users:all"],
    "role-permissions": ["role-permissions:matrix"],
  }[key];

  keys.forEach((item) => cache.delete(item));
}

export function warmCommonLookups() {
  void getCachedStudents();
  void getCachedGuardians();
}
