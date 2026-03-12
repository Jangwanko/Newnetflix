import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 20,
  duration: "2m",
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:18080";

export default function () {
  const paths = ["/", "/movies/", "/livez", "/readyz", "/movie/999999/"];
  const path = paths[Math.floor(Math.random() * paths.length)];
  const res = http.get(`${BASE_URL}${path}`);
  check(res, {
    "status is 200/404": (r) => r.status === 200 || r.status === 404,
  });
  sleep(0.2);
}
