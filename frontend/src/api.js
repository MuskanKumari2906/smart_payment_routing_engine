const API = "http://localhost:8000";

export async function get(path) {
  const res = await fetch(API + path);
  return res.json();
}

export async function post(path) {
  const res = await fetch(API + path, { method: "POST" });
  return res.json();
}
