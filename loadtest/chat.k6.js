import http from "k6/http";
import { check, sleep } from "k6";
export const options = { vus: 20, duration: "1m", thresholds: { http_req_failed: ["rate<0.01"], http_req_duration: ["p(95)<800"] } };
export function setup() {
  const r = http.post(`${__ENV.BASE}/api/auth/token`, { username: __ENV.USER, password: __ENV.PASS });
  return { token: r.json("access_token") };
}
export default function (d) {
  const r = http.get(`${__ENV.BASE}/api/stats`, { headers: { Authorization: `Bearer ${d.token}` } });
  check(r, { ok: (x) => x.status === 200 });
  sleep(1);
}
