#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const nodeCrypto = require("node:crypto");
const dns = require("node:dns").promises;
const readline = require("node:readline/promises");
const { stdin: input, stdout: output } = require("node:process");
const axios = require("axios");
const CryptoJS = require("crypto-js");
const JSEncrypt = require("jsencrypt");

const EMBEDDED_APP_PACKAGE = {
  name: "dmghg",
  version: "1.1.9",
};
const EMBEDDED_APP_ENV = {
  MAIN_VITE_APPID: "4150439554430627",
  MAIN_VITE_APP_INTERNAL_VERSION: "1.0.0",
  MAIN_VITE_CLIENT_RECEIVE:
    "LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFb1FJQkFBS0NBUUVBdmJIZ1RDN0M1RGNwc2M3R1BEWnRENVo5cVFYb2hPYjVkRHZ5dDJBeGtGbk1ORlNzClRGcnZzdy81amtCUUVOb3hGbEhKTnVEL204c2l0TldUOGVDR0V0dE9xd0lqcWhUZkxMMDhhU2VRZUh3T3RqMWgKNHp0NE9hR3Breko1VlMyTVI0d0JiQWJzZDkraW1XR0J2aGQ0dG54a0VwU3ZNZEZtOEZ1MG9rV0xVc3MyODZHcwpwc1hQUTVUMHUrd3lFekw3Y2ZlOXFmRTJUbHNBalppQVZheVZpQ2o0bnVWRDBpVEVRWXVIT2lxK09mUDFiNElzCjUzcnZ5UkZBeU43Z3ZmdHhNOU9NYWlveHFkV0l5MWNHUU9iQnJGNnNKV2JZVytOUmt6enBlNHo1RkppeW5QK0wKck9RejM2dTVtRFN4NkxTcll3VXVvSlBSOWo4V2J3RXJ5cko1SFFJREFRQUJBb0lCQUJHeVlIeDYrRStXSGR1cQpzSys1WEI5U0tOTDE3Q1ZKN3dlNjkvL0hoNWd4NkcwUllTbVdhanBJU1QzT0hpb1VVUFFHR1VGM2FDRStxRFE2Cm9KeTJGNHYyemJZQ2N4VlE4U2taVm1Ody8zZGVDM2xRN0tyb1IyVUpBZXJya0lvenY1eUZJVFRVeUlhK1pFcnUKMzgyK0h0TFhjL2FQekhCWFdzVWRxUkppYm9jQXFPYUlSUDg5VHFQand0amhvbDBibGFBWnVCbG5KQVhUNHRWOAppditaeURabkJKRnpkUU5BNXk4NnBVakFVc3FoVnM5NUpVSENseXZTaGFBNHl5OUpJV3RWS3NzK1dMK1dBLzdSCm5ndTR3MmF5NW4wcXlUbHpoVjJoMlYxNGVjbjVDNjJvVVpNK1lseEQ5RDZvRmFidUN4clZVVUxaMzJ4WkM1RFQKTXNZd3dua0NnWUVBd3FRSGV3b1EwK0syM3BxY2gvV2xKaXFSZE5tUFdpMXk0WEkxSGNuTTZpQ2xBUlQ3YmlxTwpzR2pIcG1HS3NFNkI0N29lWEpleEVmVHVPWTA1OWFRRC95VGRoZktTZkRWd2pRUjVBQjlXeUlKeWNtOXl5TVUzCjcyOWRTbVhvVzZTbkVMZnNEVVB0c0xSVzZFOHJKOWx2OTVZQ1BPQ0QvcDVweHBoVzdxbXVSQk1DZ1lFQStYNnoKUUo5ZnZNWFlCckhVZ3VTY2lvS2grL215OGtlWmRia0VacVRMMUprS0ZOUXhGRzU2UWJ0ZzlRMm1oWXdrTmxxSQpDeVVBcmI1Sy94UXZIaTVOZ01jVjdQNEk3YnQxcW0yZFFVZmg2UEMyMVBkTmV5LzRaRnBXdnE4UXdkaXJvM1RjCmwweStWb0hvV1plUzNSYm0wMnN1MGtHUVJrL2JyZzNSc3JxSkZBOENnWUFTRjhWS1BxbEp5TzFPeS9oNCt2Q2IKRjZIbHhzTjRrbmozVS9KMERtb3A2VmJ0UHRJUWI0eE1BYkZ0V2V2V2I3WExRV1hKSGFDc0ZxUitYUTVpTXhqYwpBc1ZFeWtPcm9Cd1NQN1F2dXJvS2NYWEtCV29hRjVzWGVyYWxUOHZGbVF5ZWxUb3dFWHhxekppM2g0UnZjOXJnCm5PVWdXNDVwZ0xnOGFiVExBcUxjV1FLQmdRQzRpWWhZTWdtRC9Pb04rWlp2d2x3dTd2U1ZCVm5nYmlrSnMvR1gKWWlrSmRMREtPekNhSmlUelhYOFhnaU03QUM4QXJQR1hIS1ZsM1N4bmd5eGVyR3pTNVc1SVBwV29FVkcwM3lMRApXRUcySStWM20vdUpOREFMT2U2VFY3V1RTNG1ZZXlWMkcyTmxaT3pRNTVYUFJkTXhhVVBXYkh3a0pZa2RNa2Q2ClpSSmk3UUovUnRZZUZVYW5nU053Z09lUjZPMG0vQXNjRFRkVVZJZGlZeVhmSjg3OVR3QVpzK3Y4bXRxQU0wbjcKb1phVTVkSFhMRWVlSElZL2pDSWZNVlJ6WXJhUkdVVy9NS0xLQTNXUk9YNS9kczFKT2VBdktoS3ZPK0gzNTZ1YQorbFQzMDZhL0QxVGpjUXhlRXl1MkpVRkJpS0NKWWJvazkvK2FnaW8wSHZoa3BDQWtudz09Ci0tLS0tRU5EIFJTQSBQUklWQVRFIEtFWS0tLS0tCg==",
  MAIN_VITE_CLIENT_SEND:
    "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUF2dy9FaDNnZEkwRDV3eDloWDM0QwpOYWl1aWNhNHNyMFYvNExnd2hxTFBnY29QOTJyRllRMzFhanVRU2ZJZHNQampBQnJkd01Hc2c2aXJnKzNnTk9kCkZWZm04VW12czZGUWY2QUcwYnF6VThDM1ZqSWV0WE5tSG5ncWJBaTl5VnQ4L0RtT1NNRWM3U2VRYUpBUmpnUTUKRmdwV1hpMkp3bzc3WWpyNkFuQThWT3VMKzY2THpVcU5xTFlzSGNFc2Y3c0dUTnY0L01xSnpNZEZ0R3dXVWVnZgp3TGlpTkRxbHFOaTVqbU1JMGpVSWNKb0R3NzdUOXJOOHIvazllZTA3VUNxRVdhb3RTUk5zTXl6RzdjYUJqSTlNCjh3c0EwWGxuWmU2cTJmSjQweS92OE16UlFOaGJONyswV2RRSk81RlI4STI5SEEycHozaUVnMEU4YUttckg4dnoKTHdJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg==",
  MAIN_VITE_PLANFORM: "3",
  MAIN_VITE_VERSION: "2024-09-24",
};

function safeReadText(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (_) {
    return "";
  }
}

function loadPackageInfo() {
  const packageJsonPath = path.join(__dirname, "package.json");
  const packageText = safeReadText(packageJsonPath);
  const packageInfo = safeJsonParse(packageText, null);
  if (!packageInfo || typeof packageInfo !== "object") {
    return { ...EMBEDDED_APP_PACKAGE };
  }
  return {
    name: pickText(packageInfo.name, EMBEDDED_APP_PACKAGE.name),
    version: pickText(packageInfo.version, EMBEDDED_APP_PACKAGE.version),
  };
}

function extractConfigValue(bundle, key) {
  const patterns = [
    new RegExp(`"${key}"\\s*:\\s*"([^"]*)"`),
    new RegExp(`${key}\\s*:\\s*"([^"]*)"`),
  ];

  for (const pattern of patterns) {
    const match = bundle.match(pattern);
    if (match) {
      return match[1];
    }
  }

  throw new Error(`无法从主进程文件中提取 ${key}`);
}

function buildHostSeedsFromAppId(appId) {
  const md5Suffix = CryptoJS.MD5(appId).toString().substring(24);
  return [
    `http://${md5Suffix}3.staticcard.vps.jp:7862`,
    `http://${md5Suffix}3.staticcard.jpy.jp:7862`,
    `http://${md5Suffix}3.staticcard.whalece.org:7862`,
    `http://${md5Suffix}3.staticcard.judian.jp:7862`,
  ];
}

function extractHostSeeds(bundle) {
  const appId = extractConfigValue(bundle, "MAIN_VITE_APPID");
  return buildHostSeedsFromAppId(appId);
}

function pickConfigValue(bundle, key) {
  try {
    return extractConfigValue(bundle, key);
  } catch (_) {
    return pickText(EMBEDDED_APP_ENV[key]);
  }
}

function loadAppConfig(appPackage) {
  const mainBundlePath = path.join(__dirname, "out", "main", "index.js");
  const mainBundle = safeReadText(mainBundlePath);
  const appId = pickConfigValue(mainBundle, "MAIN_VITE_APPID");
  return {
    mainBundle,
    appId,
    appVersion: appPackage.version,
    internalVersion: pickConfigValue(
      mainBundle,
      "MAIN_VITE_APP_INTERNAL_VERSION",
    ),
    platform: pickConfigValue(mainBundle, "MAIN_VITE_PLANFORM"),
    requestVersion: pickConfigValue(mainBundle, "MAIN_VITE_VERSION"),
    clientSend: pickConfigValue(mainBundle, "MAIN_VITE_CLIENT_SEND"),
    clientReceive: pickConfigValue(mainBundle, "MAIN_VITE_CLIENT_RECEIVE"),
    hostSeeds: mainBundle
      ? extractHostSeeds(mainBundle)
      : buildHostSeedsFromAppId(appId),
  };
}

const APP_PACKAGE = loadPackageInfo();
const APP_CONFIG = loadAppConfig(APP_PACKAGE);
const FALLBACK_HOSTS = ["http://bkbf.xn--vhqr42drhf5k7b.com"];

const REMOTE_RSA_PRIVATE_KEY_STR =
  "MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAK2obrvkb/npsEjqvvuJcVgGigOcdtvjGMGggufULIf6u4otOsofcBHdk3QZ2H/0qnf9Na7q6wmmE1+kuWJlEUO1/G/coBLrb3J3H7W6L2QR0dIYccEnD1P5qRaXdJvSWgSRIqzPQcP1A1a9BTwiDpQ9v77NTWGqi4JfbY24eI5TAgMBAAECgYABQd9vX9OJuS3sETsJwjB+ZSm5pffcVrQWrs1T1V7vKxsRgItU7E5Y6sRHCmrdXk2fqccqOYwzGS85uY0YD8hEtK580SCz1XKAgVqe/loPi7lYJH1W1xN29WWtS1JjNSN5HnPlWwQbGwkTxo1Om9u/SJ/fYphVXriwLP8bP+VCWQJBANOQJtRABQS4OYAHyyVbW6RBZ5d64Y/Kjhf1ZlIKRa9QDWCRlNg6XrJ0tZ5xt9RK1SDRZDniu6Eku3YHuI0/CJkCQQDSIhpNbDbS1554x1dO7oZATdufL+JVjZa/o6tqizslo5aoD7ahREuOh7e1mI4yDqmaA6jSsRL9OyG4a11lN8XLAkEAxe/kpEiRaW0DPyoLgpQLFY6r4Snyx5l3gCr05GT/9ZosKeGLJRLXbpeLJQa4O0MYTHAcGZxsd8PqL+/hVyVWYQJBAMFucxfiDXV41oAHv+8A0sRO52RaB9cJR0ORvjGNiRzUwdJi5JL+8y548DtR+1NI/AayZ63LItfInvnMm2SZOpECQFtjgv08sKNyKgFKOumAl55A4/Ai4LX7w1US2HGAeOJwL8G6nipePA8KbGBzjvXH9Lfr8GEuy1DdCxYcxhwnmWg=";
const REMOTE_RSA_PUBLIC_KEY_STR =
  "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDkmujpECrpxvCCF5iHnXDhSb4a8OODNg7x2dUggK0JNWzbw3Oz30aIZxzXm0dfVTRhuO+Upv0gtkwx5WVW1oLzwxAcQwmWx5G0F5B3yglsGZoDJZwgZmp7zrowOkyR59zKy4CHwbjwcxaSBVXtJ/NIZ21x63p663Nxjj1ZTIkl3wIDAQAB";
const REMOTE_LOGIN_URL = "http://111.230.160.82/v2/user/login";
const REMOTE_USER_INFO_URL = "http://111.230.160.82/user/info";
const REMOTE_FUND_URL = "http://111.230.160.82/user/fund/getFund";
const REMOTE_ORDER_SCAN_URL = "http://64.120.95.181:2026/pc/order/scan";
const REMOTE_ORDER_INFO_URL = "http://111.230.160.82/order/info/getApiOrder";
const REMOTE_ORDER_PAY_URL = "http://111.230.160.82/v2/order/info/payApiOrder";
const REMOTE_TIMEOUT_MS = 20000;
const REMOTE_ANDROID_MODELS = [
  "22041211AC",
  "SM-G9910",
  "KB2000",
  "V2049A",
  "M2102K1C",
];
let cachedToken = "";

const cryptoCommon = {
  mode: CryptoJS.mode.CBC,
  padding: CryptoJS.pad.Pkcs7,
};

const { Utf8, Base64 } = CryptoJS.enc;

function printHelp() {
  console.log(
    `
用法:
  node test-vip.js           启动全自动一条龙服务 (登录 -> 默认套餐 -> 输数量 -> 自动支付)
  node test-vip.js <action> --host <https://example.com> [options]
  node test-vip.js --account <name> --password <pwd> [--pretty]
  node test-vip.js <account> <password> [--pretty]

动作:
  onepath                   全自动一条龙服务 (默认动作，自动选默认套餐)
  menu                      启动交互菜单，列出接口供选择
  smoke                     一键检测：自动解析 host，测试 list，可选顺带测试 login
  list                      获取 VIP 套餐列表
  record                    获取 VIP 开通记录
  buy                       创建 VIP 购买请求
  batch                     一条命令批量下单并自动支付
  autopay                   使用聚点 Android 远端接口自动扣钻支付
  status                    查询订单状态
  login                     登录并打印 token
  info                      获取当前用户信息
  raw                       自定义加密请求

通用参数:
  --host <url>              后端 host，例如 https://api.example.com
  --token <token>           登录态 token，record/buy/info 通常需要
  --json <json>             直接传入 JSON 请求体
  --pretty                  格式化输出 JSON

通用参数:
  --host <url>              后端 host，例如 https://api.example.com
  --token <token>           登录态 token，record/buy/info 通常需要
  --json <json>             直接传入 JSON 请求体
  --pretty                  格式化输出 JSON

record 参数:
  --page <n>                页码，默认 1
  --limit <n>               每页数量，默认 10

buy 参数:
  --vip-id <id>             套餐 id
  --v-id <id>               当前视频 id，真实前端下单时会携带
  --player <value>          当前播放线路/播放器标识
  --part <value>            当前分集/分段标识
  --count <n>               批量创建订单数量；大于 1 时需配合 --single-buy
  --batch-output <path>     批量下单结果输出文件，默认当前目录自动命名
  --batch-interval-ms <ms>  批量下单间隔，默认 0
  --stop-on-error           批量下单遇错后立即停止
  --watch-timeout-ms <ms>   每次监听订单状态超时，默认 15000
  --unlock-timeout-ms <ms>  支付成功后轮询 VIP 解锁超时，默认 20000
  --unlock-poll-ms <ms>     VIP 解锁轮询间隔，默认 1500
  --max-retry-buy <n>       订单关闭/过期后自动重建次数，默认 3
  --skip-unlock-verify      支付成功后不校验 /pc/users/info 是否已解锁 VIP
  --single-buy              只创建一次订单，不自动串联支付状态流程
  --confirm-buy             确认执行 buy，避免误下单

batch 参数:
  复用 buy/autopay 的大部分参数
  --vip-id <id>             套餐 id
  --count <n>               批量数量；缺省时会在终端提示输入
  --autopay-output <path>   批量支付结果输出文件，默认当前目录自动命名
  --progress-jsonl          输出机器可读进度事件，供后端实时同步
  --confirm-buy             确认执行 batch，避免误下单

autopay 参数:
  --scan-url <url>          扫码链接，优先推荐直接传 buy 返回的 qr_code
  --order-no <no>           订单号，可与 scan-url 二选一或同时传
  --trade-no <no>           已知真实 tradeNo 时可直接传
  --batch-file <path>       批量支付输入文件，使用 buy --count 生成的结果
  --batch-output <path>     批量支付结果输出文件，默认当前目录自动命名
  --batch-interval-ms <ms>  批量支付每笔间隔，默认 0
  --stop-on-error           批量支付遇错后立即停止
  --remote-token <token>    复用 Android 远端 token，缺省则用 --account/--password 登录
  --settle-attempts <n>     支付后轮询余额/订单次数，默认 8
  --settle-interval-ms <ms> 支付后轮询间隔，默认 1000
  --query-retry <n>         解析 tradeNo 时每个候选重试次数，默认 2
  --query-interval-ms <ms>  解析 tradeNo 时重试间隔，默认 600
  --debug-autopay           打印扫码结果、候选订单、tradeNo 和支付原始响应

status 参数:
  --order-no <no>           订单号
  --timeout-ms <ms>         最长等待毫秒数，默认 15000

login 参数:
  --json '{"type":"password","account":"xxx","password":"yyy"}'
  或
  --type password --account <name> --password <pwd>

smoke 参数:
  --account <name>          可选，带上则顺手测试登录
  --password <pwd>          可选，带上则顺手测试登录

raw 参数:
  --method <GET|POST>
  --path <path>             例如 /pc/vip_price/list
  --json <json>

示例:
  node test-vip.js
  node test-vip.js menu
  node test-vip.js smoke --pretty
  node test-vip.js smoke --account demo@qq.com --password 123456 --pretty
  node test-vip.js --account demo@qq.com --password 123456 --pretty
  node test-vip.js demo@qq.com 123456 --pretty
  node test-vip.js list --host https://your-host --pretty
  node test-vip.js record --host https://your-host --token YOUR_TOKEN --page 1 --limit 10 --pretty
  node test-vip.js buy --host https://your-host --token YOUR_TOKEN --vip-id 12 --v-id 1001 --player line1 --part 1 --confirm-buy --unlock-timeout-ms 20000 --pretty
  node test-vip.js buy --host https://your-host --token YOUR_TOKEN --vip-id 12 --v-id 1001 --player line1 --part 1 --confirm-buy --single-buy --count 30 --batch-output vip-orders.json --pretty
  node test-vip.js batch --host https://your-host --token YOUR_TOKEN --vip-id 12 --confirm-buy --pretty
  node test-vip.js autopay --account demo@qq.com --password 123456 --scan-url http://64.120.95.181:2026/pc/order/scan/xxxx?jdTokenNo=xxxx --pretty
  node test-vip.js autopay --account demo@qq.com --password 123456 --batch-file vip-orders.json --batch-output vip-autopay.json --pretty
  node test-vip.js status --host https://your-host --token YOUR_TOKEN --order-no 20260424223908647882111760 --pretty
  node test-vip.js login --host https://your-host --type password --account demo --password 123456 --pretty
`,
  );
}

function parseArgs(argv) {
  const result = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const current = argv[i];
    if (!current.startsWith("--")) {
      result._.push(current);
      continue;
    }
    const key = current.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      result[key] = true;
      continue;
    }
    result[key] = next;
    i += 1;
  }
  return result;
}

function safeJsonParse(text, fallback) {
  try {
    return JSON.parse(text);
  } catch (_) {
    return fallback;
  }
}

function ensureParentDir(filePath) {
  const parentDir = path.dirname(path.resolve(filePath));
  fs.mkdirSync(parentDir, { recursive: true });
}

function createTimestampId() {
  const now = new Date();
  const yyyy = String(now.getFullYear());
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mi = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  return `${yyyy}${mm}${dd}-${hh}${mi}${ss}`;
}

function resolveBatchOutputPath(filePath, prefix) {
  const providedPath = String(filePath ?? "").trim();
  if (providedPath) {
    return path.resolve(providedPath);
  }
  return path.resolve(process.cwd(), `${prefix}-${createTimestampId()}.json`);
}

const BATCH_PROGRESS_EVENT_PREFIX = "__JD_BATCH_EVENT__";
const BATCH_PROGRESS_RESULT_PREFIX = "__JD_BATCH_RESULT__";

function isBatchProgressJsonlEnabled(args) {
  return Boolean(args?.["progress-jsonl"]);
}

function emitBatchProgressEvent(args, event) {
  if (!isBatchProgressJsonlEnabled(args)) {
    return;
  }
  const payload =
    event && typeof event === "object"
      ? {
          timestamp: new Date().toISOString(),
          ...event,
        }
      : { timestamp: new Date().toISOString() };
  console.log(`${BATCH_PROGRESS_EVENT_PREFIX}${JSON.stringify(payload)}`);
}

function emitBatchProgressResult(args, result) {
  if (!isBatchProgressJsonlEnabled(args)) {
    return;
  }
  console.log(`${BATCH_PROGRESS_RESULT_PREFIX}${JSON.stringify(result)}`);
}

function writeJsonFile(filePath, payload) {
  const resolvedPath = path.resolve(filePath);
  ensureParentDir(resolvedPath);
  fs.writeFileSync(resolvedPath, JSON.stringify(payload, null, 2), "utf8");
  return resolvedPath;
}

function readJsonFile(filePath) {
  const resolvedPath = path.resolve(filePath);
  return {
    filePath: resolvedPath,
    payload: safeJsonParse(fs.readFileSync(resolvedPath, "utf8"), null),
  };
}

function dictLike(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

function pickText(...values) {
  for (const value of values) {
    if (value == null) {
      continue;
    }
    const text = String(value).trim();
    if (text) {
      return text;
    }
  }
  return "";
}

function extractLoginToken(payload, depth = 0) {
  if (!payload || typeof payload !== "object" || depth > 4) {
    return "";
  }
  const directToken = pickText(
    payload.token,
    payload.accessToken,
    payload.access_token,
    payload.xToken,
    payload["x-token"],
    payload["X-Token"],
    payload.authorization,
    payload.Authorization,
  );
  if (directToken) {
    return directToken.replace(/^Bearer\s+/i, "").trim();
  }
  for (const value of Object.values(payload)) {
    if (!value || typeof value !== "object") {
      continue;
    }
    const nestedToken = extractLoginToken(value, depth + 1);
    if (nestedToken) {
      return nestedToken;
    }
  }
  return "";
}

function resolveLoginErrorMessage(result) {
  return pickText(
    result?.msg,
    result?.message,
    result?.data?.msg,
    result?.data?.message,
    result?.error,
    result?.data?.error,
  );
}

function cleanWrappedText(value) {
  return String(value ?? "")
    .replace(/[`"'"]/g, "")
    .trim();
}

function sanitizeUrlLike(value) {
  const text = cleanWrappedText(value);
  return /^https?:\/\//i.test(text) ? text : text;
}

function parsePositiveInt(value, fieldName) {
  const number = Number(value);
  if (!Number.isInteger(number) || number <= 0) {
    throw new Error(`${fieldName} 需要传正整数`);
  }
  return number;
}

function toPem(base64Text, label) {
  const body = String(base64Text || "")
    .replace(/\s+/g, "")
    .match(/.{1,64}/g)
    ?.join("\n");
  return `-----BEGIN ${label}-----\n${body}\n-----END ${label}-----`;
}

function buildRemoteHeaders() {
  const androidVersion = 10 + Math.floor(Math.random() * 5);
  const model =
    REMOTE_ANDROID_MODELS[
      Math.floor(Math.random() * REMOTE_ANDROID_MODELS.length)
    ];
  return {
    "User-Agent": `Dalvik/2.1.0 (Linux; U; Android ${androidVersion}; ${model} Build/UP1A.231005.007)`,
    "App-Version": "2.0.4",
    "App-Number": CryptoJS.MD5(nodeCrypto.randomUUID()).toString().slice(0, 16),
    "System-Type": "Android",
  };
}

function createRemoteContext(token, baseHeaders = buildRemoteHeaders()) {
  const authToken = String(token || "").trim();
  if (!authToken) {
    throw new Error("缺少 Android 远端 token");
  }
  return {
    token: authToken,
    headers: {
      ...baseHeaders,
      Authorization: `Bearer ${authToken}`,
    },
  };
}

function aesEncryptRemoteText(text, key) {
  return CryptoJS.AES.encrypt(text, CryptoJS.enc.Utf8.parse(key), {
    mode: CryptoJS.mode.ECB,
    padding: CryptoJS.pad.Pkcs7,
  }).toString();
}

function aesDecryptRemoteText(key, ciphertext) {
  const decrypted = CryptoJS.AES.decrypt(
    String(ciphertext || ""),
    CryptoJS.enc.Utf8.parse(key),
    {
      mode: CryptoJS.mode.ECB,
      padding: CryptoJS.pad.Pkcs7,
    },
  );
  return decrypted.toString(CryptoJS.enc.Utf8);
}

function rsaDecryptRemoteText(ciphertext) {
  const decryptor = new JSEncrypt();
  decryptor.setPrivateKey(toPem(REMOTE_RSA_PRIVATE_KEY_STR, "PRIVATE KEY"));
  const value = decryptor.decrypt(String(ciphertext || "").trim());
  if (!value) {
    throw new Error("远端 RSA 解密失败");
  }
  return value;
}

function getRemoteSecret(aesKey) {
  const encryptor = new JSEncrypt();
  encryptor.setPublicKey(toPem(REMOTE_RSA_PUBLIC_KEY_STR, "PUBLIC KEY"));
  const value = encryptor.encrypt(String(aesKey || "").trim());
  if (!value) {
    throw new Error("远端 Secret 生成失败");
  }
  return value;
}

function ensureRemotePayload(data, defaultMessage) {
  const payload =
    typeof data === "string" ? safeJsonParse(data, null) : dictLike(data);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(defaultMessage);
  }
  return payload;
}

function buildRemoteRequestHeaders(context, extraHeaders = {}) {
  return {
    ...dictLike(context).headers,
    ...extraHeaders,
  };
}

function shouldRefreshRemoteSession(message) {
  const text = String(message || "").trim();
  if (!text) {
    return false;
  }
  return [
    "异地登录",
    "未登录",
    "重新登录",
    "登录失效",
    "登录已失效",
    "登录已过期",
    "token 已失效",
    "token失效",
    "会话失效",
    "正在登录",
    "请登录",
  ].some((keyword) => text.includes(keyword));
}

function isRetryablePayMessage(message) {
  const text = String(message || "").trim();
  if (!text) {
    return false;
  }
  return ["正在登录", "订单已支付", "处理中", "请稍后"].some((keyword) =>
    text.includes(keyword),
  );
}

function isPublicOrderPayloadSuccess(payload) {
  const payloadDict = dictLike(payload);
  const orderData = dictLike(payloadDict.data);
  if (!Object.keys(orderData).length) {
    return false;
  }
  const message = pickText(
    payloadDict.msg,
    payloadDict.message,
    payloadDict.data?.msg,
    payloadDict.data?.message,
  );
  const codeText = pickText(payloadDict.code, payloadDict.status).toLowerCase();
  if (payloadDict.success === false) {
    return false;
  }
  if (
    [
      "300",
      "400",
      "401",
      "402",
      "403",
      "404",
      "500",
      "error",
      "fail",
      "failed",
    ].includes(codeText)
  ) {
    return false;
  }
  return !["失败", "错误", "不存在", "无效", "失效", "异地登录", "未登录"].some(
    (keyword) => message.includes(keyword),
  );
}

function appendUniqueText(items, ...values) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text && !items.includes(text)) {
      items.push(text);
    }
  }
}

function extractTradeTokensFromText(text) {
  const rawText = String(text || "").trim();
  const candidates = [];
  if (!rawText) {
    return candidates;
  }

  if (!rawText.startsWith("http") && !rawText.includes("?")) {
    appendUniqueText(candidates, rawText);
  }

  try {
    const parsed = new URL(rawText);
    for (const key of ["tradeNo", "jdTokenNo", "orderNo", "trade_no", "no"]) {
      appendUniqueText(candidates, ...parsed.searchParams.getAll(key));
    }
    const pathPart = parsed.pathname.split("/").filter(Boolean).pop();
    if (pathPart && pathPart.length > 5) {
      appendUniqueText(candidates, pathPart);
    }
  } catch (_) {
    // Ignore invalid URLs.
  }

  const patterns = [
    /Pay\("([^"]+)"\)/g,
    /Pay\('([^']+)'\)/g,
    /tradeNo["']?\s*[:=]\s*["']?([^"'&\s]+)/gi,
    /jdTokenNo["']?\s*[:=]\s*["']?([^"'&\s]+)/gi,
    /orderNo["']?\s*[:=]\s*["']?([^"'&\s]+)/gi,
    /(AI\d{10,})/g,
    /(?<!\d)(\d{14,})(?!\d)/g,
  ];
  for (const pattern of patterns) {
    for (const match of rawText.matchAll(pattern)) {
      appendUniqueText(candidates, match[1]);
    }
  }

  return candidates;
}

function extractPublicTradeCandidate(qrText, tradeNo = "", orderNo = "") {
  const rawText = String(qrText || "").trim();
  const scanUrl = /^https?:\/\//i.test(rawText) ? rawText : "";
  const candidates = [];
  appendUniqueText(candidates, tradeNo, orderNo);
  appendUniqueText(candidates, ...extractTradeTokensFromText(rawText));
  if (candidates.length === 0) {
    throw new Error("二维码中未识别到订单标识，请确认扫到的是聚点购买二维码");
  }
  return {
    tradeCandidate: candidates[0],
    orderCandidate:
      String(orderNo || "").trim() || candidates[1] || candidates[0],
    scanUrl,
  };
}

function extractPayTradeNo(text) {
  const rawText = String(text || "");
  const patterns = [
    /Pay\("([^"]+)"\)/,
    /Pay\('([^']+)'\)/,
    /tradeNo["']?\s*[:=]\s*["']([^"']+)["']/i,
    /orderNo["']?\s*[:=]\s*["'](AI[^"']+)["']/i,
    /(AI\d{10,})/,
  ];
  for (const pattern of patterns) {
    const match = rawText.match(pattern);
    if (match) {
      return String(match[1]).trim();
    }
  }
  return "";
}

async function remoteLoginWithPassword(account, password) {
  const baseHeaders = buildRemoteHeaders();
  const aesKey = nodeCrypto.randomBytes(8).toString("hex");
  const requestPayload = {
    account,
    appKey: "android",
    code: password,
    inviteCode: "",
    type: 2,
  };
  const requestDebug = {
    account,
    appKey: requestPayload.appKey,
    type: requestPayload.type,
    inviteCode: requestPayload.inviteCode,
    hasPassword: Boolean(password),
    passwordLength: String(password || "").length,
  };
  const response = await axios({
    url: REMOTE_LOGIN_URL,
    method: "POST",
    timeout: REMOTE_TIMEOUT_MS,
    validateStatus: () => true,
    headers: {
      ...baseHeaders,
      Secret: getRemoteSecret(aesKey),
      "Content-Type": "text/plain;charset=UTF-8",
    },
    data: aesEncryptRemoteText(JSON.stringify(requestPayload), aesKey),
  });
  if (response.status >= 400) {
    const error = new Error(`聚点远端登录失败，HTTP ${response.status}`);
    error.debug = {
      stage: "REMOTE_LOGIN_HTTP",
      request: requestDebug,
      httpStatus: response.status,
      responseData: response.data ?? null,
    };
    throw error;
  }
  let payload;
  try {
    payload = ensureRemotePayload(response.data, "聚点远端登录响应异常");
  } catch (error) {
    error.debug = {
      stage: "REMOTE_LOGIN_PAYLOAD",
      request: requestDebug,
      httpStatus: response.status,
      responseData: response.data ?? null,
    };
    throw error;
  }
  const responseSecret = pickText(
    response.headers?.secret,
    response.headers?.Secret,
  );
  const encryptedData = payload.data;
  if (!responseSecret || !encryptedData) {
    const error = new Error(
      pickText(payload.msg, payload.message) || "聚点远端登录失败",
    );
    error.debug = {
      stage: "REMOTE_LOGIN_RESPONSE",
      request: requestDebug,
      httpStatus: response.status,
      payload,
      hasResponseSecret: Boolean(responseSecret),
      hasEncryptedData: Boolean(encryptedData),
    };
    throw error;
  }
  let loginPayload;
  try {
    const responseKey = rsaDecryptRemoteText(responseSecret);
    const decrypted = aesDecryptRemoteText(responseKey, String(encryptedData));
    loginPayload = ensureRemotePayload(
      safeJsonParse(decrypted, null),
      "聚点远端登录响应解密失败",
    );
  } catch (error) {
    const wrappedError = new Error(error.message || "聚点远端登录响应解密失败");
    wrappedError.debug = {
      stage: "REMOTE_LOGIN_DECRYPT",
      request: requestDebug,
      httpStatus: response.status,
      payload,
    };
    throw wrappedError;
  }
  const accessToken = pickText(loginPayload.accessToken);
  if (!accessToken) {
    const error = new Error(
      pickText(loginPayload.msg, payload.msg, payload.message) ||
        "聚点远端登录失败",
    );
    error.debug = {
      stage: "REMOTE_LOGIN_ACCESS_TOKEN",
      request: requestDebug,
      httpStatus: response.status,
      payload,
      loginPayload,
    };
    throw error;
  }
  return {
    token: accessToken,
    context: createRemoteContext(accessToken, baseHeaders),
    loginPayload,
    rawPayload: payload,
  };
}

async function ensureRemoteAutoPaySession(args, debugAutoPay = false) {
  if (args["remote-token"]) {
    return {
      context: createRemoteContext(args["remote-token"]),
      loginResult: null,
      remoteToken: String(args["remote-token"]).trim(),
    };
  }

  const credentials = getLoginCredentials(args.account, args.password);
  try {
    const loginResult = await remoteLoginWithPassword(
      credentials.account,
      credentials.password,
    );
    printAutoPayDebug(debugAutoPay, "REMOTE_LOGIN", {
      account: credentials.account,
      token: loginResult.token,
      loginPayload: loginResult.loginPayload,
      rawPayload: loginResult.rawPayload,
    });
    return {
      context: loginResult.context,
      loginResult,
      remoteToken: loginResult.token,
    };
  } catch (error) {
    printAutoPayDebug(debugAutoPay, "REMOTE_LOGIN_ERROR", {
      message: error.message,
      debug: error.debug || null,
    });
    throw error;
  }
}

function normalizeVipOrderContext(source) {
  if (!source || typeof source !== "object") {
    return null;
  }

  const videoId = Number(source.vid ?? source.v_id ?? source.id);
  if (!videoId) {
    return null;
  }
  const player =
    source.play == null || /^null$/i.test(String(source.play).trim())
      ? ""
      : String(source.play).trim();
  const part =
    source.part == null || /^null$/i.test(String(source.part).trim())
      ? ""
      : String(source.part).trim();

  return {
    "v-id": String(videoId),
    player,
    part,
  };
}

function scoreVipOrderContext(context) {
  if (!context) {
    return 0;
  }
  let score = 0;
  if (context["v-id"]) {
    score += 2;
  }
  if (context.player) {
    score += 2;
  }
  if (context.part) {
    score += 1;
  }
  return score;
}

async function fetchPlayHistory(host, token, page = 1, limit = 10) {
  const result = await sendEncryptedRequest({
    host,
    path: `/pc/history?limit=${limit}&page=${page}`,
    method: "GET",
    token,
  });
  return Array.isArray(result?.data?.items) ? result.data.items : [];
}

function selectServerVipOrderContext(items, currentContext = {}) {
  const currentVideoId = String(currentContext["v-id"] ?? "").trim();
  let bestMatch = null;

  for (const item of items) {
    const normalized = normalizeVipOrderContext({
      vid: item?.vid ?? item?.v_id ?? item?.id,
      play: item?.play ?? item?.player,
      part: item?.part,
    });
    if (!normalized) {
      continue;
    }

    let score = scoreVipOrderContext(normalized);
    if (currentVideoId && normalized["v-id"] === currentVideoId) {
      score += 3;
    }

    if (!bestMatch || score > bestMatch.score) {
      bestMatch = {
        context: normalized,
        score,
      };
    }

    if (score >= 8) {
      break;
    }
  }

  return bestMatch?.context ?? null;
}

async function loadServerVipOrderContext(host, token, currentContext = {}) {
  try {
    const items = await fetchPlayHistory(host, token, 1, 12);
    return selectServerVipOrderContext(items, currentContext);
  } catch (_) {
    return null;
  }
}

function isEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

function ensureHost(host) {
  if (!host) {
    throw new Error("缺少 --host");
  }
  return host.endsWith("/") ? host.slice(0, -1) : host;
}

async function resolveHost(explicitHost) {
  if (explicitHost) {
    return ensureHost(explicitHost);
  }

  for (const seedHost of APP_CONFIG.hostSeeds) {
    try {
      const seedUrl = new URL(seedHost);
      const ips = await dns.resolve4(seedUrl.hostname);
      for (const ip of ips) {
        const requrl = `${seedUrl.protocol}//${ip}${seedUrl.port ? `:${seedUrl.port}` : ""}`;
        const response = await axios.get(`${requrl}/app/config/host`, {
          timeout: 3900,
          headers: {
            appid: APP_CONFIG.appId,
            requrl,
          },
        });
        const payload = response.data;
        if (payload && payload.code === 20000 && payload.data) {
          const hostConfig = await aesDecryptText(payload.data);
          if (hostConfig && hostConfig.host) {
            return ensureHost(hostConfig.host);
          }
        }
      }
    } catch (_) {
      // Try next seed host.
    }
  }

  for (const host of FALLBACK_HOSTS) {
    try {
      await axios.get(`${host}/pc/vip_price/list`, {
        timeout: 3900,
        headers: await buildHeaders(),
      });
      return host;
    } catch (_) {
      // Try next fallback host.
    }
  }

  throw new Error("自动发现 host 失败，请显式传入 --host");
}

async function aesEncryptText(text) {
  const key = CryptoJS.enc.Utf8.parse("ziISjqkXPsGUMRNGyWigxDGtJbfTdcGv");
  const iv = CryptoJS.enc.Utf8.parse("WonrnVkxeIxDcFbv");
  const value = CryptoJS.enc.Utf8.parse(text);
  const data = CryptoJS.enc.Base64.stringify(value);
  return CryptoJS.AES.encrypt(data, key, { iv, ...cryptoCommon }).toString();
}

async function aesDecryptText(text) {
  const key = CryptoJS.enc.Utf8.parse("ziISjqkXPsGUMRNGyWigxDGtJbfTdcGv");
  const iv = CryptoJS.enc.Utf8.parse("WonrnVkxeIxDcFbv");
  const decrypted = CryptoJS.AES.decrypt(text, key, { iv, ...cryptoCommon });
  const plain = decrypted.toString(CryptoJS.enc.Utf8);
  return safeJsonParse(Base64.parse(plain).toString(Utf8), plain);
}

async function paramsEncrypt(text) {
  let payload = text;
  if (typeof payload !== "string") {
    payload = JSON.stringify(payload);
  }
  const aesKey = "R5xThLNmXbpDOgyj";
  const aesIv = aesKey.split("").reverse().join("");
  const cert = CryptoJS.enc.Base64.parse(APP_CONFIG.clientSend).toString(
    CryptoJS.enc.Utf8,
  );
  const encryptor = new JSEncrypt();
  encryptor.setPublicKey(cert);
  const rsaEncryptedKey = encryptor.encrypt(aesKey);
  const encryptedBody = CryptoJS.AES.encrypt(
    payload,
    CryptoJS.enc.Utf8.parse(aesKey),
    { iv: CryptoJS.enc.Utf8.parse(aesIv), ...cryptoCommon },
  ).toString();
  return `${rsaEncryptedKey}.${encryptedBody}`;
}

async function paramsDecrypt(text) {
  if (typeof text !== "string") {
    return text;
  }
  const parts = text.split(".");
  if (parts.length !== 2) {
    return text;
  }
  const cert = Base64.parse(APP_CONFIG.clientReceive).toString(Utf8);
  const decryptor = new JSEncrypt();
  decryptor.setPrivateKey(cert);
  const aesKey = decryptor.decrypt(parts[0]);
  if (!aesKey) {
    throw new Error("RSA 解密失败，无法还原响应");
  }
  const aesIv = aesKey.split("").reverse().join("");
  const decrypted = CryptoJS.AES.decrypt(
    parts[1],
    CryptoJS.enc.Utf8.parse(aesKey),
    { iv: CryptoJS.enc.Utf8.parse(aesIv), ...cryptoCommon },
  );
  const plain = decrypted.toString(CryptoJS.enc.Utf8);
  return safeJsonParse(plain, plain);
}

async function buildHeaders(token) {
  const timestamp = Date.now();
  const auth = [
    APP_CONFIG.appVersion,
    timestamp,
    APP_CONFIG.platform,
    APP_CONFIG.internalVersion,
    process.platform,
  ].join("-");

  const headers = {
    "Content-Type": "application/json",
    ts: timestamp,
    "X-VERSION": APP_CONFIG.requestVersion,
    APPID: APP_CONFIG.appId,
    Authentication: await aesEncryptText(auth),
    system: process.platform === "win32" ? 3 : 4,
  };

  if (token) {
    headers["X-Token"] = token;
  }

  return headers;
}

function parseSseEvent(rawEvent) {
  if (!rawEvent || !rawEvent.trim()) {
    return null;
  }

  let type = "";
  let id = "";
  const dataLines = [];
  for (const line of rawEvent.split(/\r?\n/)) {
    if (!line || line[0] === ":") {
      continue;
    }
    if (line.startsWith("event: ")) {
      type = line.slice(7).trim();
      continue;
    }
    if (line.startsWith("id: ")) {
      id = line.slice(4).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
      continue;
    }
    dataLines.push(line.trim());
  }

  return {
    id,
    type,
    data: dataLines.join("\n").trim(),
  };
}

function interpretOrderStatusType(type) {
  if (type === "unpaid_scan") {
    return "待扫码支付";
  }
  if (type === "shipped") {
    return "支付成功";
  }
  if (type === "error") {
    return "支付失败";
  }
  if (type === "close") {
    return "订单关闭或已过期";
  }
  if (!type) {
    return "未知状态";
  }
  return type;
}

function getOrderStatusSummary(result) {
  const latest = result?.latestEvent;
  if (!latest) {
    return "未知状态";
  }

  const eventType = latest.type;
  const payload = latest.parsedData;
  if (
    eventType === "error" &&
    payload &&
    typeof payload === "object" &&
    payload.code === 404404
  ) {
    return "状态未知(状态接口无记录)";
  }

  return interpretOrderStatusType(eventType);
}

function printOrderStatusSummary(result) {
  const latest = result?.latestEvent;
  if (!latest) {
    return;
  }

  console.error("\n订单状态摘要:");
  console.error(`订单号: ${result.orderNo}`);
  console.error(`状态: ${getOrderStatusSummary(result)}`);
  if (latest.data) {
    console.error(`原始数据: ${latest.data}`);
  }
}

async function watchOrderStatus(host, orderNo, token, timeoutMs = 15000) {
  const headers = await buildHeaders(token);
  headers.Accept = "text/event-stream";
  const controller = new AbortController();
  const events = [];
  let latestEvent = null;
  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    const response = await axios({
      url: `${ensureHost(host)}/pc/order/status?order_no=${encodeURIComponent(orderNo)}`,
      method: "GET",
      headers,
      signal: controller.signal,
      responseType: "stream",
      timeout: timeoutMs + 2000,
      validateStatus: () => true,
    });

    if (response.status >= 400) {
      throw new Error(`HTTP ${response.status}`);
    }

    await new Promise((resolve, reject) => {
      let buffer = "";
      response.data.setEncoding("utf8");
      response.data.on("data", (chunk) => {
        buffer += chunk;
        let separatorIndex = buffer.search(/\r?\n\r?\n/);
        while (separatorIndex !== -1) {
          const rawEvent = buffer.slice(0, separatorIndex);
          const separatorLength = buffer[separatorIndex] === "\r" ? 4 : 2;
          buffer = buffer.slice(separatorIndex + separatorLength);
          const event = parseSseEvent(rawEvent);
          if (event) {
            event.parsedData = safeJsonParse(event.data, event.data);
            events.push(event);
            latestEvent = event;
            const isRecordNotFound =
              event.type === "error" &&
              event.parsedData &&
              typeof event.parsedData === "object" &&
              event.parsedData.code === 404404;
            if (["shipped", "close"].includes(event.type) || isRecordNotFound) {
              clearTimeout(timeoutId);
              controller.abort();
              resolve();
              return;
            }
          }
          separatorIndex = buffer.search(/\r?\n\r?\n/);
        }
      });
      response.data.on("end", resolve);
      response.data.on("error", (error) => {
        if (controller.signal.aborted) {
          resolve();
          return;
        }
        reject(error);
      });
    });
  } catch (error) {
    if (!(controller.signal.aborted || error.name === "CanceledError")) {
      throw error;
    }
  } finally {
    clearTimeout(timeoutId);
  }

  return {
    ok: true,
    orderNo,
    timedOut,
    latestEvent,
    events: events.map((event) => ({
      id: event.id,
      type: event.type,
      statusText:
        event.type === "error" &&
        event.parsedData &&
        typeof event.parsedData === "object" &&
        event.parsedData.code === 404404
          ? "状态未知(状态接口无记录)"
          : interpretOrderStatusType(event.type),
      data: event.parsedData,
    })),
  };
}

async function remoteGetUserInfo(context) {
  const aesKey = nodeCrypto.randomBytes(8).toString("hex");
  const response = await axios({
    url: REMOTE_USER_INFO_URL,
    method: "GET",
    timeout: REMOTE_TIMEOUT_MS,
    validateStatus: () => true,
    headers: buildRemoteRequestHeaders(context, {
      Secret: getRemoteSecret(aesKey),
    }),
  });
  if (response.status >= 400) {
    throw new Error(`聚点账号资料同步失败，HTTP ${response.status}`);
  }
  return ensureRemotePayload(response.data, "聚点账号资料同步失败");
}

async function remoteGetFund(context) {
  const aesKey = nodeCrypto.randomBytes(8).toString("hex");
  const response = await axios({
    url: REMOTE_FUND_URL,
    method: "GET",
    timeout: REMOTE_TIMEOUT_MS,
    validateStatus: () => true,
    headers: buildRemoteRequestHeaders(context, {
      Secret: getRemoteSecret(aesKey),
    }),
  });
  if (response.status >= 400) {
    throw new Error(`聚点钻石余额同步失败，HTTP ${response.status}`);
  }
  const payload = ensureRemotePayload(response.data, "聚点钻石余额同步失败");
  const message = pickText(
    payload.msg,
    payload.message,
    payload.data?.msg,
    payload.data?.message,
  );
  if (shouldRefreshRemoteSession(message)) {
    throw new Error(message || "聚点远端登录已失效");
  }
  return {
    diamondQuantity: Number(payload.data?.quantity ?? 0) || 0,
    payload,
  };
}

async function remoteGetOrderInfo(context, tradeNo) {
  const target = String(tradeNo || "").trim();
  if (!target) {
    throw new Error("缺少可用的 tradeNo，无法查询聚点订单");
  }
  const aesKey = nodeCrypto.randomBytes(8).toString("hex");
  const response = await axios({
    url: REMOTE_ORDER_INFO_URL,
    method: "GET",
    timeout: REMOTE_TIMEOUT_MS,
    validateStatus: () => true,
    params: {
      tradeNo: target,
    },
    headers: buildRemoteRequestHeaders(context, {
      Secret: getRemoteSecret(aesKey),
    }),
  });
  if (response.status >= 400) {
    throw new Error(`聚点订单查询失败，HTTP ${response.status}`);
  }
  const payload = ensureRemotePayload(response.data, "聚点订单查询失败");
  const message = pickText(
    payload.msg,
    payload.message,
    payload.data?.msg,
    payload.data?.message,
  );
  if (shouldRefreshRemoteSession(message)) {
    throw new Error(message || "聚点远端登录已失效");
  }
  return payload;
}

async function remoteScanQrNotify(context, orderNo, scanUrl = "") {
  const targetOrderNo = String(orderNo || "").trim();
  let targetUrl = /^https?:\/\//i.test(String(scanUrl || "").trim())
    ? String(scanUrl).trim()
    : "";
  if (!targetUrl) {
    if (!targetOrderNo) {
      return {
        status: "warn",
        message: "缺少扫码通知所需订单号，已跳过通知步骤",
      };
    }
    targetUrl = `${REMOTE_ORDER_SCAN_URL}/${targetOrderNo}?jdTokenNo=${targetOrderNo}`;
  }

  try {
    const response = await axios({
      url: targetUrl,
      method: "GET",
      timeout: 5000,
      validateStatus: () => true,
      headers: buildRemoteRequestHeaders(context, {
        "User-Agent": "Judian Android",
        "X-Requested-With": "com.fywl.fygjx",
      }),
    });
    const body =
      typeof response.data === "string"
        ? response.data.trim()
        : JSON.stringify(response.data);
    if (response.status !== 200) {
      return {
        status: "error",
        message: `扫码通知失败，HTTP ${response.status}`,
        statusCode: response.status,
      };
    }
    if (body.startsWith("<")) {
      const realTradeNo = extractPayTradeNo(body);
      return {
        status: realTradeNo ? "ok" : "warn",
        message: realTradeNo
          ? "扫码页返回跳转脚本"
          : "扫码页返回 HTML，但未解析出真实 tradeNo",
        tradeNo: realTradeNo,
        rawText: body.slice(0, 300),
      };
    }
    const payload = safeJsonParse(body, null);
    if (!payload || typeof payload !== "object") {
      const realTradeNo = extractPayTradeNo(body);
      return {
        status: ["错误", "失败", "不存在"].some((word) => body.includes(word))
          ? "error"
          : "ok",
        message: body.slice(0, 100) || "扫码通知返回了非 JSON 文本",
        tradeNo: realTradeNo,
        rawText: body.slice(0, 300),
      };
    }
    const realTradeNo = extractPayTradeNo(JSON.stringify(payload));
    if (realTradeNo && !payload.tradeNo) {
      payload.tradeNo = realTradeNo;
    }
    return payload;
  } catch (error) {
    return {
      status: "error",
      message: `扫码通知请求失败：${error.message}`,
    };
  }
}

function buildPublicOrderQueryCandidates(
  qrText,
  tradeCandidate,
  orderCandidate,
  scanResult = null,
) {
  const candidates = [];
  appendUniqueText(candidates, tradeCandidate, orderCandidate);
  appendUniqueText(candidates, ...extractTradeTokensFromText(qrText));
  const resultPayload = dictLike(scanResult);
  for (const key of ["tradeNo", "jdTokenNo", "orderNo", "no"]) {
    appendUniqueText(candidates, resultPayload[key]);
  }
  appendUniqueText(
    candidates,
    ...extractTradeTokensFromText(resultPayload.rawText),
  );
  appendUniqueText(
    candidates,
    ...extractTradeTokensFromText(resultPayload.message),
  );
  if (Object.keys(resultPayload).length > 0) {
    appendUniqueText(
      candidates,
      ...extractTradeTokensFromText(JSON.stringify(resultPayload)),
    );
  }
  return candidates;
}

async function resolvePublicOrderPayload(
  context,
  {
    qrText,
    tradeCandidate,
    orderCandidate,
    scanResult = null,
    maxAttemptsPerCandidate = 2,
    sleepMs = 600,
  },
) {
  const candidates = buildPublicOrderQueryCandidates(
    qrText,
    tradeCandidate,
    orderCandidate,
    scanResult,
  );
  if (candidates.length === 0) {
    throw new Error("二维码中未识别到订单标识，请确认扫到的是聚点购买二维码");
  }

  const trace = [];
  let hadInvalidPayload = false;
  let lastInvalidMessage = "";
  let lastRemoteError = "";

  for (const candidate of candidates) {
    for (
      let attemptIndex = 0;
      attemptIndex < maxAttemptsPerCandidate;
      attemptIndex += 1
    ) {
      try {
        const payload = await remoteGetOrderInfo(context, candidate);
        const message = pickText(
          payload.msg,
          payload.message,
          payload.data?.msg,
          payload.data?.message,
        );
        const orderData = dictLike(payload.data);
        const ok = isPublicOrderPayloadSuccess(payload);
        trace.push({
          candidate,
          attempt: attemptIndex + 1,
          ok,
          hasData: Object.keys(orderData).length > 0,
          message: message.slice(0, 120),
        });
        if (ok) {
          return {
            effectiveTradeNo: candidate,
            orderPayload: payload,
            trace,
          };
        }
        hadInvalidPayload = true;
        if (message) {
          lastInvalidMessage = message;
        }
      } catch (error) {
        lastRemoteError = error.message;
        trace.push({
          candidate,
          attempt: attemptIndex + 1,
          ok: false,
          error: lastRemoteError,
        });
      }

      if (attemptIndex < maxAttemptsPerCandidate - 1) {
        await delay(sleepMs);
      }
    }
  }

  if (hadInvalidPayload) {
    throw new Error(
      lastInvalidMessage ||
        "未查询到有效订单，请确认二维码是否已过期或扫码链路是否已失效",
    );
  }
  throw new Error(lastRemoteError || "聚点订单查询失败，请稍后重试");
}

async function remotePayOrder(context, tradeNo) {
  const target = String(tradeNo || "").trim();
  if (!target) {
    throw new Error("缺少可用的 tradeNo，无法发起支付");
  }
  const aesKey = nodeCrypto.randomBytes(8).toString("hex");
  const response = await axios({
    url: REMOTE_ORDER_PAY_URL,
    method: "POST",
    timeout: REMOTE_TIMEOUT_MS,
    validateStatus: () => true,
    headers: buildRemoteRequestHeaders(context, {
      Secret: getRemoteSecret(aesKey),
      "Content-Type": "application/json; charset=utf-8",
    }),
    data: {
      tradeNo: target,
    },
  });
  if (response.status >= 400) {
    throw new Error(`聚点支付请求失败，HTTP ${response.status}`);
  }
  const payload = ensureRemotePayload(response.data, "聚点支付失败");
  const message = pickText(
    payload.msg,
    payload.message,
    payload.data?.msg,
    payload.data?.message,
  );
  const codeText = pickText(payload.code, payload.status).toLowerCase();
  if (
    payload.success === false ||
    ["400", "401", "402", "403", "500", "error", "fail", "failed"].includes(
      codeText,
    ) ||
    message.includes("失败") ||
    message.includes("不足")
  ) {
    const error = new Error(message || "聚点支付失败");
    error.payload = payload;
    error.httpStatus = response.status;
    error.tradeNo = target;
    throw error;
  }
  return payload;
}

async function waitRemotePaymentSettle(
  context,
  tradeNo,
  { beforeDiamond, maxAttempts = 8, sleepMs = 1000 } = {},
) {
  let afterDiamond = Number(beforeDiamond || 0);
  let lastOrderPayload = {};
  let lastFundPayload = {};
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (attempt > 0) {
      await delay(sleepMs);
    }
    try {
      const fundResult = await remoteGetFund(context);
      afterDiamond = fundResult.diamondQuantity;
      lastFundPayload = fundResult.payload;
    } catch (_) {
      // Ignore transient balance polling errors.
    }
    try {
      lastOrderPayload = await remoteGetOrderInfo(context, tradeNo);
    } catch (_) {
      // Ignore transient order polling errors.
    }
    if (afterDiamond < beforeDiamond) {
      return {
        settled: true,
        afterDiamond,
        lastOrderPayload,
        lastFundPayload,
      };
    }
  }
  return {
    settled: false,
    afterDiamond,
    lastOrderPayload,
    lastFundPayload,
  };
}

async function runAutoPayFlow(args, shared = null) {
  const debugAutoPay = Boolean(args["debug-autopay"]);
  const scanUrl = String(args["scan-url"] ?? "").trim();
  const tradeNoInput = String(args["trade-no"] ?? "").trim();
  const orderNoInput = String(args["order-no"] ?? "").trim();
  if (!scanUrl && !tradeNoInput && !orderNoInput) {
    throw new Error("autopay 需要 --scan-url 或 --trade-no 或 --order-no");
  }

  const remoteSession =
    shared?.remoteSession ??
    (await ensureRemoteAutoPaySession(args, debugAutoPay));
  const loginResult = remoteSession.loginResult;
  const context = remoteSession.context;

  let beforeDiamond = 0;
  let beforeFundPayload = {};
  const debugInfo = {
    input: {
      scanUrl,
      tradeNo: tradeNoInput,
      orderNo: orderNoInput,
      queryRetry: Math.max(1, Number(args["query-retry"] ?? 2)),
      queryIntervalMs: Math.max(100, Number(args["query-interval-ms"] ?? 600)),
      settleAttempts: Math.max(1, Number(args["settle-attempts"] ?? 8)),
      settleIntervalMs: Math.max(
        200,
        Number(args["settle-interval-ms"] ?? 1000),
      ),
    },
    remote: {
      loggedIn: Boolean(loginResult || args["remote-token"]),
    },
  };
  try {
    const fundResult = await remoteGetFund(context);
    beforeDiamond = fundResult.diamondQuantity;
    beforeFundPayload = fundResult.payload;
    debugInfo.beforeFundPayload = beforeFundPayload;
    printAutoPayDebug(debugAutoPay, "FUND_BEFORE", {
      diamondQuantity: beforeDiamond,
      payload: beforeFundPayload,
    });
  } catch (_) {
    // Continue with 0 when fund lookup fails; later polling may still confirm settlement.
  }
  debugInfo.beforeDiamond = beforeDiamond;

  const {
    tradeCandidate,
    orderCandidate,
    scanUrl: normalizedScanUrl,
  } = extractPublicTradeCandidate(scanUrl, tradeNoInput, orderNoInput);
  debugInfo.extracted = {
    tradeCandidate,
    orderCandidate,
    normalizedScanUrl,
  };
  const scanResult = await remoteScanQrNotify(
    context,
    orderCandidate || tradeCandidate,
    normalizedScanUrl,
  );
  debugInfo.scanResult = scanResult;
  printAutoPayDebug(debugAutoPay, "SCAN_RESULT", scanResult);
  let { effectiveTradeNo, orderPayload, trace } =
    await resolvePublicOrderPayload(context, {
      qrText: scanUrl,
      tradeCandidate,
      orderCandidate,
      scanResult,
      maxAttemptsPerCandidate: Math.max(1, Number(args["query-retry"] ?? 2)),
      sleepMs: Math.max(100, Number(args["query-interval-ms"] ?? 600)),
    });
  debugInfo.orderQueryTrace = trace;
  debugInfo.orderPayload = orderPayload;
  printAutoPayDebug(debugAutoPay, "ORDER_QUERY", {
    effectiveTradeNo,
    orderPayload,
    trace,
  });

  effectiveTradeNo = pickText(orderPayload?.data?.tradeNo, effectiveTradeNo);
  debugInfo.effectiveTradeNo = effectiveTradeNo;
  debugInfo.effectiveOrderNo = pickText(
    orderPayload?.data?.orderNo,
    orderCandidate,
  );

  let payPayload = null;
  let afterDiamond = beforeDiamond;
  let afterFundPayload = {};
  let settled = false;
  let settledByPolling = false;

  try {
    payPayload = await remotePayOrder(context, effectiveTradeNo);
    debugInfo.payPayload = payPayload;
    printAutoPayDebug(debugAutoPay, "PAY_RESPONSE", payPayload);
    try {
      const fundResult = await remoteGetFund(context);
      afterDiamond = fundResult.diamondQuantity;
      afterFundPayload = fundResult.payload;
      settled = afterDiamond < beforeDiamond;
      debugInfo.afterFundPayload = afterFundPayload;
      printAutoPayDebug(debugAutoPay, "FUND_AFTER_PAY", {
        diamondQuantity: afterDiamond,
        payload: afterFundPayload,
        settled,
      });
    } catch (_) {
      // Ignore and fall back to polling below.
    }
  } catch (error) {
    debugInfo.payError = {
      message: error.message,
      tradeNo: error.tradeNo || effectiveTradeNo,
      httpStatus: error.httpStatus || null,
      payload: error.payload || null,
      orderNo:
        pickText(orderPayload?.data?.orderNo, orderCandidate) || "unknown",
    };
    printAutoPayDebug(debugAutoPay, "PAY_ERROR", debugInfo.payError);
    printAutoPayDebug(debugAutoPay, "SNAPSHOT_ON_ERROR", debugInfo);
    if (!isRetryablePayMessage(error.message)) {
      throw new Error(
        `${error.message} | tradeNo=${effectiveTradeNo || "unknown"} | orderNo=${
          pickText(orderPayload?.data?.orderNo, orderCandidate) || "unknown"
        }`,
      );
    }
    payPayload = {
      success: true,
      msg: error.message,
      settledByPolling: true,
    };
  }

  if (!settled) {
    const settleResult = await waitRemotePaymentSettle(
      context,
      effectiveTradeNo,
      {
        beforeDiamond,
        maxAttempts: Math.max(1, Number(args["settle-attempts"] ?? 8)),
        sleepMs: Math.max(200, Number(args["settle-interval-ms"] ?? 1000)),
      },
    );
    settled = settleResult.settled;
    settledByPolling = settleResult.settled;
    afterDiamond = settleResult.afterDiamond;
    debugInfo.settleResult = settleResult;
    printAutoPayDebug(debugAutoPay, "SETTLE_RESULT", settleResult);
    if (Object.keys(settleResult.lastFundPayload).length > 0) {
      afterFundPayload = settleResult.lastFundPayload;
    }
    if (isPublicOrderPayloadSuccess(settleResult.lastOrderPayload)) {
      orderPayload = settleResult.lastOrderPayload;
      effectiveTradeNo = pickText(
        settleResult.lastOrderPayload?.data?.tradeNo,
        effectiveTradeNo,
      );
    }
  }
  debugInfo.afterDiamond = afterDiamond;
  debugInfo.afterFundPayload = afterFundPayload;
  debugInfo.settled = settled;
  printAutoPayDebug(debugAutoPay, "FINAL_STATE", debugInfo);

  return {
    ok: settled,
    pending: !settled,
    settledByPolling,
    tradeNo: effectiveTradeNo,
    orderNo: pickText(orderPayload?.data?.orderNo, orderCandidate),
    beforeDiamond,
    afterDiamond,
    consumedDiamond: Math.max(0, beforeDiamond - afterDiamond),
    login: summarizeRemoteLogin(loginResult),
    scanResult,
    orderPayload,
    payPayload,
    beforeFundPayload,
    afterFundPayload,
    orderQueryTrace: trace,
    debug: debugAutoPay ? debugInfo : void 0,
    remoteUserInfo: await remoteGetUserInfo(context).catch(() => null),
  };
}

async function sendEncryptedRequest({
  host,
  path,
  method = "GET",
  data,
  token,
}) {
  const headers = await buildHeaders(token);
  const hasBody = data && Object.keys(data).length > 0;
  const url = /^https?:\/\//i.test(path) ? path : `${ensureHost(host)}${path}`;
  const response = await axios({
    url,
    method,
    timeout: 9000,
    validateStatus: () => true,
    transformRequest: [(requestData) => requestData],
    headers,
    data: hasBody ? await paramsEncrypt(data) : void 0,
  });

  if (response.status >= 400) {
    const body =
      typeof response.data === "string"
        ? response.data
        : JSON.stringify(response.data);
    throw new Error(`HTTP ${response.status}: ${body}`);
  }

  if (typeof response.data !== "string") {
    return response.data;
  }

  return paramsDecrypt(response.data);
}

function printResult(result, pretty) {
  if (pretty) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }
  console.log(JSON.stringify(result));
}

function printAutoPayDebug(enabled, stage, payload) {
  if (!enabled) {
    return;
  }
  console.error(`\n[AUTOPAY DEBUG] ${stage}`);
  console.error(JSON.stringify(payload, null, 2));
}

function printAutoPaySummary(result) {
  if (!result || typeof result !== "object") {
    return;
  }
  console.error("\n自动支付摘要:");
  if (result.tradeNo) {
    console.error(`tradeNo: ${result.tradeNo}`);
  }
  if (result.orderNo) {
    console.error(`orderNo: ${result.orderNo}`);
  }
  console.error(
    `状态: ${result.ok ? "已支付" : result.pending ? "处理中" : "失败"}`,
  );
  console.error(`支付前钻石: ${result.beforeDiamond}`);
  console.error(`支付后钻石: ${result.afterDiamond}`);
  console.error(`本次扣钻: ${result.consumedDiamond}`);
}

function printBatchBuySummary(result) {
  if (!result || typeof result !== "object") {
    return;
  }
  console.error("\n批量下单摘要:");
  console.error(`目标数量: ${result.count}`);
  console.error(`成功数量: ${result.createdCount}`);
  console.error(`失败数量: ${result.failedCount}`);
  if (result.outputFile) {
    console.error(`结果文件: ${result.outputFile}`);
  }
}

function printBatchAutoPaySummary(result) {
  if (!result || typeof result !== "object") {
    return;
  }
  console.error("\n批量支付摘要:");
  console.error(`目标数量: ${result.count}`);
  console.error(`成功数量: ${result.successCount}`);
  console.error(`失败数量: ${result.failedCount}`);
  if (result.outputFile) {
    console.error(`结果文件: ${result.outputFile}`);
  }
}

function printBatchCreateAndAutoPaySummary(result) {
  if (!result || typeof result !== "object") {
    return;
  }
  console.error("\n批量下单并自动支付摘要:");
  if (result.vipId) {
    console.error(`vip_id: ${result.vipId}`);
  }
  if (result.count) {
    console.error(`订单数量: ${result.count}`);
  }
  if (Number.isFinite(result.unitDiamond)) {
    console.error(`单笔钻石: ${result.unitDiamond}`);
  }
  if (Number.isFinite(result.requiredDiamond)) {
    console.error(`预计总消耗: ${result.requiredDiamond}`);
  }
  if (Number.isFinite(result.availableDiamond)) {
    console.error(`当前钻石: ${result.availableDiamond}`);
  }
  if (result.phase) {
    console.error(`流程阶段: ${result.phase}`);
  }
  if (result.buyResult?.outputFile) {
    console.error(`下单结果文件: ${result.buyResult.outputFile}`);
  }
  if (result.autoPayResult?.outputFile) {
    console.error(`支付结果文件: ${result.autoPayResult.outputFile}`);
  }
}

function getLoginCredentials(account, password) {
  const finalAccount = String(account ?? "").trim();
  const finalPassword = String(password ?? "").trim();
  if (!finalAccount || !finalPassword) {
    throw new Error(
      "请提供动漫共和国的账户和密码 (使用 --account/--password 或在提示时输入)",
    );
  }
  return {
    account: finalAccount,
    password: finalPassword,
  };
}

async function promptLoginCredentials(args) {
  const rl = readline.createInterface({ input, output });
  try {
    const account =
      String(args.account ?? "").trim() ||
      (await rl.question("请输入动漫共和国账号: ")).trim();
    const password =
      String(args.password ?? "").trim() ||
      (await rl.question("请输入动漫共和国密码: ")).trim();

    if (!account || !password) {
      throw new Error("账号和密码不能为空");
    }

    args.account = account;
    args.password = password;
    return { account, password };
  } finally {
    rl.close();
  }
}

async function runPasswordLogin(host, account, password) {
  const payload = {
    enum: isEmail(account) ? 1 : 0,
    email: isEmail(account) ? account : "",
    phone: isEmail(account) ? "" : account,
    type: "password",
    password,
    symbol: process.platform,
  };
  return sendEncryptedRequest({
    host,
    path: "/pc/users/login",
    method: "POST",
    data: payload,
  });
}

async function ensureToken(host, token, account, password) {
  if (token) {
    return token;
  }
  if (cachedToken) {
    return cachedToken;
  }

  const credentials = getLoginCredentials(account, password);
  const result = await runPasswordLogin(
    host,
    credentials.account,
    credentials.password,
  );
  const nextToken = extractLoginToken(result);
  if (!nextToken) {
    const detail = resolveLoginErrorMessage(result);
    throw new Error(
      detail
        ? `自动登录成功但未识别 token: ${detail}`
        : "自动登录成功但未识别 token",
    );
  }
  cachedToken = nextToken;
  return nextToken;
}

async function fetchVipPlans(host, token) {
  const result = await sendEncryptedRequest({
    host,
    path: "/pc/vip_price/list",
    method: "GET",
    token,
  });
  return Array.isArray(result?.data) ? result.data : [];
}

async function fetchVideoDetail(host, videoId, token) {
  return sendEncryptedRequest({
    host,
    path: `/pc/video/detail?id=${videoId}`,
    method: "GET",
    token,
  });
}

async function fetchUserInfo(host, token) {
  return sendEncryptedRequest({
    host,
    path: "/pc/users/info",
    method: "GET",
    token,
  });
}

async function fetchVipRecords(host, token, page = 1, limit = 10) {
  return sendEncryptedRequest({
    host,
    path: `/pc/users/vip_records?page=${page}&limit=${limit}`,
    method: "GET",
    token,
  });
}

function findFirstStringByKeys(source, keys) {
  if (!source || typeof source !== "object") {
    return "";
  }
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function findFirstScanUrl(source) {
  if (!source || typeof source !== "object") {
    return "";
  }

  const visited = new Set();
  const queue = [source];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || typeof current !== "object" || visited.has(current)) {
      continue;
    }
    visited.add(current);

    for (const [key, value] of Object.entries(current)) {
      if (typeof value === "string") {
        const nextValue = value.trim();
        if (
          /^https?:\/\//i.test(nextValue) &&
          (/\/scan\//i.test(nextValue) || /(scan|pay|qrcode|qr)/i.test(key))
        ) {
          return nextValue;
        }
      } else if (value && typeof value === "object") {
        queue.push(value);
      }
    }
  }

  return "";
}

function extractBuyOrderInfo(result) {
  const data = result?.data;
  if (!data || typeof data !== "object") {
    return {
      orderNo: "",
      scanUrl: "",
    };
  }

  return {
    orderNo: findFirstStringByKeys(data, [
      "order_no",
      "order_sn",
      "orderNo",
      "orderSn",
      "trade_no",
      "tradeNo",
    ]),
    scanUrl: sanitizeUrlLike(findFirstScanUrl(data)),
  };
}

function summarizeRemoteLogin(loginResult) {
  if (!loginResult) {
    return null;
  }
  if (loginResult.accessTime || loginResult.expireTime) {
    return {
      accessTime: pickText(loginResult.accessTime),
      expireTime: pickText(loginResult.expireTime),
      isRegister: Boolean(loginResult.isRegister),
    };
  }
  if (!loginResult.loginPayload) {
    return null;
  }
  return {
    accessTime: pickText(loginResult.loginPayload.accessTime),
    expireTime: pickText(loginResult.loginPayload.expireTime),
    isRegister: Boolean(loginResult.loginPayload.isRegister),
  };
}

function summarizeCreateResult(createResult) {
  return {
    code: createResult?.code ?? null,
    message: pickText(createResult?.message, createResult?.msg),
    orderNo: pickText(
      createResult?.data?.order_no,
      createResult?.data?.orderNo,
      findFirstStringByKeys(createResult?.data, ["order_no", "orderNo"]),
    ),
    scanUrl: sanitizeUrlLike(
      pickText(createResult?.data?.qr_code, createResult?.data?.qrCode),
    ),
    diamond: Number(createResult?.data?.diamond ?? 0) || 0,
    amount: Number(createResult?.data?.amount ?? 0) || 0,
    expireAt: pickText(
      createResult?.data?.expire_at,
      createResult?.data?.expireAt,
    ),
  };
}

function summarizeAutoPayResult(result) {
  return {
    ok: Boolean(result?.ok),
    pending: Boolean(result?.pending),
    settledByPolling: Boolean(result?.settledByPolling),
    tradeNo: pickText(result?.tradeNo),
    orderNo: pickText(result?.orderNo),
    beforeDiamond: Number(result?.beforeDiamond ?? 0) || 0,
    afterDiamond: Number(result?.afterDiamond ?? 0) || 0,
    consumedDiamond: Number(result?.consumedDiamond ?? 0) || 0,
    login: summarizeRemoteLogin(result?.login),
    scanResult: {
      status: pickText(result?.scanResult?.status),
      message: pickText(result?.scanResult?.message),
      tradeNo: pickText(result?.scanResult?.tradeNo),
    },
    orderInfo: {
      diamond: Number(result?.orderPayload?.data?.diamond ?? 0) || 0,
      status: Number(result?.orderPayload?.data?.status ?? 0) || 0,
      orderNo: pickText(result?.orderPayload?.data?.orderNo),
      tradeNo: pickText(result?.orderPayload?.data?.tradeNo),
      remark: pickText(result?.orderPayload?.data?.remark),
      createTime: pickText(result?.orderPayload?.data?.createTime),
    },
    beforeFund: Number(result?.beforeFundPayload?.data?.quantity ?? 0) || 0,
    afterFund: Number(result?.afterFundPayload?.data?.quantity ?? 0) || 0,
    remoteUser: {
      id: Number(result?.remoteUserInfo?.data?.id ?? 0) || 0,
      account: pickText(result?.remoteUserInfo?.data?.account),
      nickName: pickText(result?.remoteUserInfo?.data?.nickName),
    },
  };
}

function summarizeBatchBuyOrder(item) {
  if (!item || typeof item !== "object") {
    return item;
  }
  if (!item.ok) {
    return {
      index: Number(item.index ?? 0) || 0,
      ok: false,
      error: pickText(item.error),
    };
  }
  return {
    index: Number(item.index ?? 0) || 0,
    ok: true,
    orderNo: pickText(item.orderNo),
    scanUrl: sanitizeUrlLike(item.scanUrl),
    createResult: summarizeCreateResult(item.createResult),
  };
}

function summarizeBatchAutoPayItem(item) {
  if (!item || typeof item !== "object") {
    return item;
  }
  if (!item.ok) {
    return {
      index: Number(item.index ?? 0) || 0,
      ok: false,
      orderNo: pickText(item.orderNo),
      scanUrl: sanitizeUrlLike(item.scanUrl),
      error: pickText(item.error),
    };
  }
  return {
    index: Number(item.index ?? 0) || 0,
    ok: true,
    orderNo: pickText(item.orderNo),
    scanUrl: sanitizeUrlLike(item.scanUrl),
    result: summarizeAutoPayResult(item.result),
  };
}

function findVipPlanById(plans, vipId) {
  const targetId = String(vipId ?? "").trim();
  if (!targetId) {
    return null;
  }
  return (
    plans.find((plan) => String(plan?.id ?? "").trim() === targetId) ?? null
  );
}

function extractVipPlanDiamondCost(plan) {
  return (
    Number(
      plan?.coin ??
        plan?.coins ??
        plan?.diamond ??
        plan?.diamond_quantity ??
        plan?.price ??
        0,
    ) || 0
  );
}

async function resolveVipId(host, token, vipId) {
  const explicitVipId = String(vipId ?? "").trim();
  const plans = await fetchVipPlans(host, token);
  if (plans.length === 0) {
    throw new Error("未获取到可购买套餐");
  }

  if (explicitVipId) {
    const selectedPlan = findVipPlanById(plans, explicitVipId);
    if (!selectedPlan) {
      throw new Error(`未找到 vip_id=${explicitVipId} 的套餐`);
    }
    return {
      vipId: String(selectedPlan.id),
      plan: selectedPlan,
      autoSelected: false,
    };
  }

  const defaultPlan = plans[0];
  return {
    vipId: String(defaultPlan.id),
    plan: defaultPlan,
    autoSelected: true,
  };
}

async function buildBatchPurchasePlan(host, token, vipId, count, args) {
  const plans = await fetchVipPlans(host, token);
  const selectedPlan = findVipPlanById(plans, vipId);
  if (!selectedPlan) {
    throw new Error(`未找到 vip_id=${vipId} 的套餐，无法预估钻石消耗`);
  }

  const unitDiamond = extractVipPlanDiamondCost(selectedPlan);
  if (unitDiamond <= 0) {
    throw new Error(
      `套餐 vip_id=${vipId} 未返回有效钻石单价，无法自动预检查余额`,
    );
  }

  const remoteSession = await ensureRemoteAutoPaySession(
    args,
    Boolean(args["debug-autopay"]),
  );
  const fundResult = await remoteGetFund(remoteSession.context);
  const availableDiamond = fundResult.diamondQuantity;
  const requiredDiamond = unitDiamond * count;

  return {
    selectedPlan,
    unitDiamond,
    count,
    requiredDiamond,
    availableDiamond,
    enoughDiamond: availableDiamond >= requiredDiamond,
    remoteSession,
    remoteFundPayload: fundResult.payload,
  };
}

async function runBatchBuyFlow(host, token, payload, args) {
  const count = Math.max(1, Number(args.count ?? 1));
  const intervalMs = Math.max(0, Number(args["batch-interval-ms"] ?? 0));
  const stopOnError = Boolean(args["stop-on-error"]);
  const outputFile = resolveBatchOutputPath(args["batch-output"], "vip-orders");
  const orders = [];

  emitBatchProgressEvent(args, {
    type: "buy_phase_started",
    total: count,
    outputFile,
  });

  for (let index = 1; index <= count; index += 1) {
    try {
      const createResult = await createVipOrder(host, token, payload);
      const { orderNo, scanUrl } = extractBuyOrderInfo(createResult);
      orders.push({
        index,
        ok: true,
        orderNo,
        scanUrl,
        createResult,
      });
      console.error(
        `批量下单 ${index}/${count} 成功: ${orderNo || "无订单号"}`,
      );
      emitBatchProgressEvent(args, {
        type: "buy_item",
        index,
        total: count,
        ok: true,
        orderNo,
        scanUrl: sanitizeUrlLike(scanUrl),
      });
    } catch (error) {
      orders.push({
        index,
        ok: false,
        error: error.message,
      });
      console.error(`批量下单 ${index}/${count} 失败: ${error.message}`);
      emitBatchProgressEvent(args, {
        type: "buy_item",
        index,
        total: count,
        ok: false,
        error: error.message,
      });
      if (stopOnError) {
        break;
      }
    }

    if (index < count && intervalMs > 0) {
      await delay(intervalMs);
    }
  }

  const result = {
    ok: orders.every((item) => item.ok),
    mode: "batch_buy",
    count,
    createdCount: orders.filter((item) => item.ok).length,
    failedCount: orders.filter((item) => !item.ok).length,
    intervalMs,
    stopOnError,
    outputFile,
    payload,
    orders: orders.map(summarizeBatchBuyOrder),
  };
  writeJsonFile(outputFile, result);
  return result;
}

function normalizeBatchAutoPayItems(batchPayload) {
  if (Array.isArray(batchPayload)) {
    return batchPayload;
  }
  if (Array.isArray(batchPayload?.orders)) {
    return batchPayload.orders;
  }
  if (Array.isArray(batchPayload?.items)) {
    return batchPayload.items;
  }
  throw new Error("批量文件格式无效，未找到 orders/items 数组");
}

async function runBatchAutoPayItems(sourceItems, args, options = {}) {
  const intervalMs = Math.max(0, Number(args["batch-interval-ms"] ?? 0));
  const stopOnError = Boolean(args["stop-on-error"]);
  const outputFile =
    options.outputFile ??
    resolveBatchOutputPath(args["batch-output"], "vip-autopay");
  const items = [];
  const remoteSession =
    options.remoteSession ??
    (await ensureRemoteAutoPaySession(args, Boolean(args["debug-autopay"])));

  emitBatchProgressEvent(args, {
    type: "autopay_phase_started",
    total: sourceItems.length,
    outputFile,
    sourceFile: options.sourceFile || "",
  });

  for (let index = 0; index < sourceItems.length; index += 1) {
    const sourceItem =
      sourceItems[index] && typeof sourceItems[index] === "object"
        ? sourceItems[index]
        : {};
    const orderNo = pickText(sourceItem.orderNo, sourceItem.order_no);
    const scanUrl = sanitizeUrlLike(
      pickText(sourceItem.scanUrl, sourceItem.scan_url, sourceItem.qr_code),
    );

    if (!orderNo && !scanUrl) {
      items.push({
        index: index + 1,
        ok: false,
        error: "缺少 orderNo/scanUrl，已跳过",
      });
      console.error(
        `批量支付 ${index + 1}/${sourceItems.length} 跳过: 缺少 orderNo/scanUrl`,
      );
      emitBatchProgressEvent(args, {
        type: "autopay_item",
        index: index + 1,
        total: sourceItems.length,
        ok: false,
        orderNo,
        scanUrl: sanitizeUrlLike(scanUrl),
        error: "缺少 orderNo/scanUrl，已跳过",
      });
      if (stopOnError) {
        break;
      }
      continue;
    }

    try {
      const payResult = await runAutoPayFlow(
        {
          ...args,
          "scan-url": scanUrl || args["scan-url"],
          "order-no": orderNo || args["order-no"],
        },
        {
          remoteSession,
        },
      );
      items.push({
        index: index + 1,
        ok: true,
        orderNo: payResult.orderNo || orderNo,
        scanUrl: sanitizeUrlLike(scanUrl),
        result: payResult,
      });
      console.error(
        `批量支付 ${index + 1}/${sourceItems.length} 成功: ${
          payResult.orderNo || orderNo || "未知订单"
        }`,
      );
      emitBatchProgressEvent(args, {
        type: "autopay_item",
        index: index + 1,
        total: sourceItems.length,
        ok: true,
        orderNo: payResult.orderNo || orderNo,
        tradeNo: payResult.tradeNo,
        scanUrl: sanitizeUrlLike(scanUrl),
        consumedDiamond: Number(payResult.consumedDiamond ?? 0) || 0,
        message: pickText(payResult?.scanResult?.message, "自动支付成功"),
      });
    } catch (error) {
      items.push({
        index: index + 1,
        ok: false,
        orderNo,
        scanUrl: sanitizeUrlLike(scanUrl),
        error: error.message,
      });
      console.error(
        `批量支付 ${index + 1}/${sourceItems.length} 失败: ${error.message}`,
      );
      emitBatchProgressEvent(args, {
        type: "autopay_item",
        index: index + 1,
        total: sourceItems.length,
        ok: false,
        orderNo,
        scanUrl: sanitizeUrlLike(scanUrl),
        error: error.message,
      });
      if (stopOnError) {
        break;
      }
    }

    if (index < sourceItems.length - 1 && intervalMs > 0) {
      await delay(intervalMs);
    }
  }

  const result = {
    ok: items.every((item) => item.ok),
    mode: "batch_autopay",
    count: sourceItems.length,
    successCount: items.filter((item) => item.ok).length,
    failedCount: items.filter((item) => !item.ok).length,
    intervalMs,
    stopOnError,
    sourceFile: options.sourceFile || "",
    outputFile,
    items: items.map(summarizeBatchAutoPayItem),
  };
  writeJsonFile(outputFile, result);
  return result;
}

async function runBatchAutoPayFlow(args) {
  const batchFile = String(args["batch-file"] ?? "").trim();
  if (!batchFile) {
    throw new Error("autopay 批量模式需要 --batch-file");
  }

  const { filePath, payload } = readJsonFile(batchFile);
  if (!payload) {
    throw new Error(`批量文件不是有效 JSON: ${filePath}`);
  }

  const sourceItems = normalizeBatchAutoPayItems(payload);
  return runBatchAutoPayItems(sourceItems, args, {
    sourceFile: filePath,
  });
}

async function runBatchCreateAndAutoPayFlow(host, token, payload, args) {
  const count = await resolveBatchCountArg(args, {
    defaultValue: 1,
    promptIfMissing: true,
  });
  if (count < 1) {
    throw new Error("batch 至少需要创建 1 个订单");
  }

  const vipId = pickText(payload?.extend?.vip_id, payload?.extend?.vipId);
  if (!vipId) {
    throw new Error("batch 缺少 vip_id，无法预检查钻石");
  }

  const precheck = await buildBatchPurchasePlan(
    host,
    token,
    vipId,
    count,
    args,
  );
  if (!precheck.enoughDiamond) {
    return {
      ok: false,
      mode: "batch_create_and_autopay",
      phase: "precheck",
      message: "远端钻石余额不足，已停止，未创建订单",
      vipId,
      count,
      unitDiamond: precheck.unitDiamond,
      requiredDiamond: precheck.requiredDiamond,
      availableDiamond: precheck.availableDiamond,
      selectedPlan: precheck.selectedPlan,
    };
  }

  const buyResult = await runBatchBuyFlow(host, token, payload, {
    ...args,
    count,
    "single-buy": true,
  });
  const payableItems = buyResult.orders.filter((item) => item && item.ok);
  const autoPayResult = await runBatchAutoPayItems(payableItems, args, {
    remoteSession: precheck.remoteSession,
    outputFile: resolveBatchOutputPath(args["autopay-output"], "vip-autopay"),
    sourceFile: buyResult.outputFile,
  });

  return {
    ok: buyResult.ok && autoPayResult.ok,
    mode: "batch_create_and_autopay",
    phase: autoPayResult.ok ? "completed" : "autopay_partial_failed",
    vipId,
    count,
    unitDiamond: precheck.unitDiamond,
    requiredDiamond: precheck.requiredDiamond,
    availableDiamond: precheck.availableDiamond,
    selectedPlan: precheck.selectedPlan,
    buyResult,
    autoPayResult,
  };
}

function printBuySummary(result) {
  const { orderNo, scanUrl } = extractBuyOrderInfo(result);
  if (!orderNo && !scanUrl) {
    return;
  }

  console.error("\n下单摘要:");
  if (orderNo) {
    console.error(`订单号: ${orderNo}`);
  }
  if (scanUrl) {
    console.error(`扫码链接: ${scanUrl}`);
  }
}

function shouldRegenerateOrder(statusResult) {
  const latest = statusResult?.latestEvent;
  if (!latest) {
    return false;
  }

  if (latest.type === "close") {
    return true;
  }

  return (
    latest.type === "error" &&
    latest.parsedData &&
    typeof latest.parsedData === "object" &&
    latest.parsedData.code === 404404
  );
}

function normalizeUserVipList(result) {
  const vips = result?.data?.vips;
  return Array.isArray(vips) ? vips : [];
}

function hasUnlockedVip(result) {
  return normalizeUserVipList(result).length > 0;
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function waitForVipUnlock(host, token, options = {}) {
  const timeoutMs = Math.max(1000, Number(options.timeoutMs ?? 20000));
  const pollMs = Math.max(300, Number(options.pollMs ?? 1500));
  const startedAt = Date.now();
  let attempts = 0;
  let lastInfo = null;
  let lastError = "";

  while (Date.now() - startedAt <= timeoutMs) {
    attempts += 1;
    try {
      lastInfo = await fetchUserInfo(host, token);
      if (hasUnlockedVip(lastInfo)) {
        return {
          ok: true,
          verified: true,
          timedOut: false,
          attempts,
          timeoutMs,
          pollMs,
          elapsedMs: Date.now() - startedAt,
          userInfo: lastInfo,
          vipCount: normalizeUserVipList(lastInfo).length,
        };
      }
    } catch (error) {
      lastError = error.message;
    }

    const remainingMs = timeoutMs - (Date.now() - startedAt);
    if (remainingMs <= 0) {
      break;
    }
    await delay(Math.min(pollMs, remainingMs));
  }

  let recordResult = null;
  try {
    recordResult = await fetchVipRecords(host, token, 1, 10);
  } catch (_) {
    // Ignore record lookup failures; user info polling is the primary signal.
  }

  return {
    ok: false,
    verified: false,
    timedOut: true,
    attempts,
    timeoutMs,
    pollMs,
    elapsedMs: Date.now() - startedAt,
    userInfo: lastInfo,
    vipCount: normalizeUserVipList(lastInfo).length,
    recordResult,
    lastError,
  };
}

async function createVipOrder(host, token, payload) {
  return sendEncryptedRequest({
    host,
    path: "/pc/order/create",
    method: "POST",
    data: payload,
    token,
  });
}

async function runBuyPaymentFlow(host, token, payload, options = {}) {
  const watchTimeoutMs = Number(options.watchTimeoutMs ?? 15000);
  const unlockTimeoutMs = Number(options.unlockTimeoutMs ?? 20000);
  const unlockPollMs = Number(options.unlockPollMs ?? 1500);
  const verifyUnlock = options.verifyUnlock !== false;
  const maxAttempts = Math.max(1, Number(options.maxAttempts ?? 3));
  const attempts = [];
  let finalState = "unknown";

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const createResult = await createVipOrder(host, token, payload);
    const { orderNo, scanUrl } = extractBuyOrderInfo(createResult);
    const attemptResult = {
      attempt,
      createResult,
      orderNo,
      scanUrl,
      statusResult: null,
      unlockResult: null,
    };
    attempts.push(attemptResult);

    if (!orderNo) {
      finalState = "created_without_order_no";
      break;
    }

    console.error(`\n第 ${attempt} 次下单已创建，开始监听订单状态...`);
    const statusResult = await watchOrderStatus(
      host,
      orderNo,
      token,
      watchTimeoutMs,
    );
    attemptResult.statusResult = statusResult;

    if (statusResult?.latestEvent?.type === "shipped") {
      finalState = "paid";
      if (verifyUnlock) {
        console.error("支付成功，开始校验 VIP 是否已解锁...");
        const unlockResult = await waitForVipUnlock(host, token, {
          timeoutMs: unlockTimeoutMs,
          pollMs: unlockPollMs,
        });
        attemptResult.unlockResult = unlockResult;
        finalState = unlockResult.ok
          ? "vip_unlocked"
          : "paid_but_unlock_pending";
      }
      break;
    }

    if (shouldRegenerateOrder(statusResult) && attempt < maxAttempts) {
      finalState = "regenerated";
      console.error("订单已关闭/过期，正在重新生成订单...");
      continue;
    }

    if (shouldRegenerateOrder(statusResult)) {
      finalState = "closed";
      break;
    }

    finalState = statusResult?.timedOut ? "watch_timeout" : "pending";
    break;
  }

  return {
    ok: verifyUnlock ? finalState === "vip_unlocked" : finalState === "paid",
    finalState,
    maxAttempts,
    watchTimeoutMs,
    unlockTimeoutMs,
    unlockPollMs,
    verifyUnlock,
    attempts: attempts.map((item) => ({
      attempt: item.attempt,
      orderNo: item.orderNo,
      scanUrl: item.scanUrl,
      createResult: item.createResult,
      statusResult: item.statusResult,
      unlockResult: item.unlockResult,
    })),
    latestAttempt: attempts[attempts.length - 1] ?? null,
  };
}

function printBuyFlowSummary(result) {
  const latestAttempt = result?.latestAttempt;
  if (!latestAttempt) {
    return;
  }

  const latestStatus = latestAttempt.statusResult;
  console.error("\n支付流程摘要:");
  console.error(`最终状态: ${result.finalState}`);
  console.error(`尝试次数: ${result.attempts.length}/${result.maxAttempts}`);
  if (latestAttempt.orderNo) {
    console.error(`当前订单号: ${latestAttempt.orderNo}`);
  }
  if (latestAttempt.scanUrl) {
    console.error(`当前扫码链接: ${latestAttempt.scanUrl}`);
  }
  if (latestStatus?.latestEvent) {
    console.error(`订单状态: ${getOrderStatusSummary(latestStatus)}`);
  }
  if (latestAttempt.unlockResult) {
    console.error(
      `VIP 解锁校验: ${latestAttempt.unlockResult.ok ? "已解锁" : "未在超时内确认"}`,
    );
    console.error(`VIP 数量: ${latestAttempt.unlockResult.vipCount}`);
  }
}

function shouldUseChainedBuyFlow(args) {
  return !args["single-buy"];
}

function getBuyFlowOptions(args) {
  return {
    watchTimeoutMs: Number(args["watch-timeout-ms"] ?? 15000),
    unlockTimeoutMs: Number(args["unlock-timeout-ms"] ?? 20000),
    unlockPollMs: Number(args["unlock-poll-ms"] ?? 1500),
    maxAttempts: Number(args["max-retry-buy"] ?? 3),
    verifyUnlock: !args["skip-unlock-verify"],
  };
}

function buildBuyPayload(args, vipId) {
  return {
    type: 1,
    extend: {
      vip_id: Number(vipId),
      v_id: Number(args["v-id"]),
      player: String(args.player ?? ""),
      part: String(args.part ?? ""),
    },
  };
}

function validateBuyPayload(payload) {
  if (!payload.extend.vip_id) {
    throw new Error("buy 需要 --vip-id 或 --json");
  }
  if (!payload.extend.v_id || !payload.extend.player || !payload.extend.part) {
    throw new Error(
      "buy 缺少上下文参数，请提供 --v-id --player --part，或直接用 --json 传完整 /pc/order/create 请求体",
    );
  }
}

function printSingleBuyResult(result, pretty) {
  printResult(result, pretty);
  printBuySummary(result);
}

function printBuyFlowResult(result, pretty) {
  printResult(result, pretty);
  const latestCreateResult = result?.latestAttempt?.createResult;
  if (latestCreateResult) {
    printBuySummary(latestCreateResult);
  }
  printBuyFlowSummary(result);
}

async function resolveVipOrderContext(host, token, args) {
  const resolved = {
    "v-id": String(args["v-id"] ?? "").trim(),
    player: String(args.player ?? "").trim(),
    part: String(args.part ?? "").trim(),
  };

  if (resolved["v-id"] && resolved.player && resolved.part) {
    return resolved;
  }

  const serverContext = await loadServerVipOrderContext(host, token, resolved);
  const merged = {
    "v-id": resolved["v-id"] || serverContext?.["v-id"] || "",
    player: resolved.player || serverContext?.player || "",
    part: resolved.part || serverContext?.part || "",
  };
  return await fillVipOrderContextFromVideoDetail(host, token, merged);
}

async function fillVipOrderContextFromVideoDetail(host, token, context) {
  if (!context["v-id"] || (context.player && context.part)) {
    return context;
  }

  try {
    const detail = await fetchVideoDetail(host, Number(context["v-id"]), token);
    const data = detail?.data;
    const defaultPart = Array.isArray(data?.parts?.[0]?.part)
      ? data.parts[0].part[0]
      : data?.parts?.[0]?.part;
    const nextContext = {
      "v-id": context["v-id"],
      player:
        context.player ||
        String(data?.history?.player ?? data?.parts?.[0]?.play ?? "").trim(),
      part:
        context.part || String(data?.history?.part ?? defaultPart ?? "").trim(),
    };
    return nextContext;
  } catch (_) {
    return context;
  }
}

async function promptVipOrderContext(args) {
  const rl = readline.createInterface({ input, output });
  try {
    console.log("\n下单上下文:");
    console.log("真实前端创建 VIP 订单时，除 vip_id 外还会附带当前视频信息。");

    const videoId =
      String(args["v-id"] ?? "").trim() ||
      (await rl.question("请输入当前视频 v_id: ")).trim();
    const player =
      String(args.player ?? "").trim() ||
      (await rl.question("请输入当前 player: ")).trim();
    const part =
      String(args.part ?? "").trim() ||
      (await rl.question("请输入当前 part: ")).trim();

    return {
      "v-id": videoId,
      player,
      part,
    };
  } finally {
    rl.close();
  }
}

async function promptBatchCount(defaultValue = 1) {
  const rl = readline.createInterface({ input, output });
  try {
    const answer = (
      await rl.question(
        `请输入要创建并自动支付的订单数量(默认 ${defaultValue}): `,
      )
    ).trim();
    return parsePositiveInt(answer || String(defaultValue), "count");
  } finally {
    rl.close();
  }
}

async function resolveBatchCountArg(args, options = {}) {
  const defaultValue = Math.max(1, Number(options.defaultValue ?? 1));
  if (args.count != null && String(args.count).trim()) {
    return parsePositiveInt(args.count, "count");
  }
  if (options.promptIfMissing && process.stdin.isTTY) {
    const count = await promptBatchCount(defaultValue);
    args.count = String(count);
    return count;
  }
  return defaultValue;
}

async function promptMenuSelection() {
  const rl = readline.createInterface({ input, output });
  try {
    console.log("\n可选接口:");
    console.log("  1. smoke  一键检测");
    console.log("  2. list   VIP 套餐列表");
    console.log("  3. login  默认账号登录");
    console.log("  4. info   当前用户信息");
    console.log("  5. record VIP 开通记录");
    console.log("  6. buy    创建购买请求");
    console.log("  7. batch  批量下单并自动支付");
    console.log("  8. status 查询订单状态");
    console.log("  9. autopay 自动扣钻支付");
    console.log("  10. raw   自定义请求");
    console.log("  0. exit   退出");
    console.log(`\n默认账号: ${DEFAULT_LOGIN.account}`);

    const choice = (await rl.question("\n请选择编号: ")).trim();
    if (choice === "0" || choice.toLowerCase() === "q") {
      return null;
    }
    if (choice === "1") {
      return { action: "smoke", overrides: { pretty: true } };
    }
    if (choice === "2") {
      return { action: "list", overrides: { pretty: true } };
    }
    if (choice === "3") {
      return { action: "login", overrides: { pretty: true } };
    }
    if (choice === "4") {
      return { action: "info", overrides: { pretty: true } };
    }
    if (choice === "5") {
      const page = (await rl.question("页码(默认 1): ")).trim() || "1";
      const limit = (await rl.question("每页数量(默认 10): ")).trim() || "10";
      return {
        action: "record",
        overrides: { page, limit, pretty: true },
      };
    }
    if (choice === "6") {
      const confirm = (
        await rl.question("确认购买请输入 yes，将直接使用默认套餐: ")
      ).trim();
      return {
        action: "buy",
        overrides: {
          "confirm-buy": /^(y|yes)$/i.test(confirm),
          "interactive-buy": true,
          pretty: true,
        },
      };
    }
    if (choice === "7") {
      const confirm = (
        await rl.question("确认批量购买请输入 yes，随后会提示输入数量: ")
      ).trim();
      return {
        action: "batch",
        overrides: {
          "confirm-buy": /^(y|yes)$/i.test(confirm),
          "interactive-buy": true,
          pretty: true,
        },
      };
    }
    if (choice === "8") {
      const orderNo = (await rl.question("订单号: ")).trim();
      const timeoutMs = (await rl.question("等待毫秒(默认 15000): ")).trim();
      return {
        action: "status",
        overrides: {
          "order-no": orderNo,
          "timeout-ms": timeoutMs || "15000",
          pretty: true,
        },
      };
    }
    if (choice === "9") {
      const scanUrl = (await rl.question("扫码链接(可留空): ")).trim();
      const orderNo = (await rl.question("订单号(可留空): ")).trim();
      return {
        action: "autopay",
        overrides: {
          "scan-url": scanUrl || void 0,
          "order-no": orderNo || void 0,
          pretty: true,
        },
      };
    }
    if (choice === "10") {
      const method = (
        (await rl.question("请求方法(默认 GET): ")).trim() || "GET"
      ).toUpperCase();
      const path = (await rl.question("请求路径: ")).trim();
      const json = (await rl.question("JSON 请求体(可留空): ")).trim();
      return {
        action: "raw",
        overrides: {
          method,
          path,
          json: json || void 0,
          pretty: true,
        },
      };
    }

    throw new Error("无效选择");
  } finally {
    rl.close();
  }
}

async function runOnePathFlow(host, args) {
  console.error("--- 启动一条龙全自动服务 ---");

  // 1. 登录
  await promptLoginCredentials(args);
  const token = await ensureToken(host, null, args.account, args.password);
  console.error("登录成功");

  // 2. 获取套餐
  const vipSelection = await resolveVipId(host, token, args["vip-id"]);
  const vipId = vipSelection.vipId;
  if (vipSelection.autoSelected) {
    console.error(
      `已自动选择默认套餐: vip_id=${vipId} (${vipSelection.plan?.title ?? "unknown"})`,
    );
  }

  // 3. 准备下单上下文
  Object.assign(args, await resolveVipOrderContext(host, token, args));
  if (!args["v-id"] || !args.player || !args.part) {
    Object.assign(args, await promptVipOrderContext(args));
  }

  // 4. 获取数量并执行
  const count = await resolveBatchCountArg(args, {
    defaultValue: 1,
    promptIfMissing: true,
  });

  const payload = buildBuyPayload(args, vipId);
  validateBuyPayload(payload);

  // 强制开启确认
  args["confirm-buy"] = true;

  console.error(`\n即将开始: 套餐ID=${vipId}, 数量=${count}`);
  const result = await runBatchCreateAndAutoPayFlow(host, token, payload, args);
  return result;
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const knownActions = new Set([
    "onepath",
    "menu",
    "smoke",
    "list",
    "record",
    "buy",
    "batch",
    "autopay",
    "status",
    "login",
    "info",
    "raw",
    "help",
  ]);
  const firstArg = args._[0];
  const hasNamedLogin = args.account && args.password;
  const hasPositionalLogin =
    firstArg &&
    !knownActions.has(firstArg) &&
    args._[1] &&
    !args.account &&
    !args.password;

  if (hasPositionalLogin) {
    args.account = args._[0];
    args.password = args._[1];
  }

  const hasNoInput = process.argv.slice(2).length === 0;
  let action = hasNoInput
    ? "onepath"
    : knownActions.has(firstArg)
      ? firstArg
      : hasNamedLogin || hasPositionalLogin
        ? "smoke"
        : "onepath";

  if (action === "menu") {
    const selection = await promptMenuSelection();
    if (!selection) {
      return;
    }
    action = selection.action;
    Object.assign(args, selection.overrides);
  }

  if (!action || action === "help" || args.help) {
    printHelp();
    return;
  }

  const pretty = Boolean(args.pretty);
  const token = args.token;
  const jsonPayload = args.json ? safeJsonParse(args.json, null) : null;
  const host =
    action === "help" || action === "autopay"
      ? args.host
      : await resolveHost(args.host);

  if (action === "onepath") {
    const result = await runOnePathFlow(host, args);
    printResult(result, pretty);
    printBatchCreateAndAutoPaySummary(result);
    return;
  }

  if (action === "smoke") {
    const credentials = getLoginCredentials(args.account, args.password);
    const result = {
      ok: true,
      host,
      list: null,
    };

    try {
      result.list = await sendEncryptedRequest({
        host,
        path: "/pc/vip_price/list",
        method: "GET",
      });
    } catch (error) {
      result.ok = false;
      result.listError = error.message;
    }

    try {
      result.login = await runPasswordLogin(
        host,
        credentials.account,
        credentials.password,
      );
      const loginToken = extractLoginToken(result.login);
      if (loginToken) {
        cachedToken = loginToken;
      }
    } catch (error) {
      result.ok = false;
      result.loginError = error.message;
    }

    printResult(result, pretty);
    return;
  }

  if (action === "list") {
    const result = await sendEncryptedRequest({
      host,
      path: "/pc/vip_price/list",
      method: "GET",
      token,
    });
    printResult(result, pretty);
    return;
  }

  if (action === "record") {
    const page = Number(args.page ?? 1);
    const limit = Number(args.limit ?? 10);
    const finalToken = await ensureToken(
      host,
      token,
      args.account,
      args.password,
    );
    const result = await sendEncryptedRequest({
      host,
      path: `/pc/users/vip_records?page=${page}&limit=${limit}`,
      method: "GET",
      token: finalToken,
    });
    printResult(result, pretty);
    return;
  }

  if (action === "buy") {
    if (!args["confirm-buy"]) {
      throw new Error("buy 操作默认拦截，请显式加上 --confirm-buy");
    }
    const finalToken = await ensureToken(
      host,
      token,
      args.account,
      args.password,
    );
    const vipSelection = await resolveVipId(host, finalToken, args["vip-id"]);
    const vipId = vipSelection.vipId;
    if (vipSelection.autoSelected) {
      console.error(
        `已自动选择默认套餐: vip_id=${vipId} (${vipSelection.plan?.title ?? "unknown"})`,
      );
    }
    if (!jsonPayload) {
      Object.assign(args, await resolveVipOrderContext(host, finalToken, args));
    }
    if (!jsonPayload && args["v-id"] && args.player && args.part) {
      console.error(
        `\n已自动带入最近播放记录: v_id=${args["v-id"]}, player=${args.player}, part=${args.part}`,
      );
    }
    if (!jsonPayload && (!args["v-id"] || !args.player || !args.part)) {
      if (process.stdin.isTTY || args["interactive-buy"]) {
        Object.assign(args, await promptVipOrderContext(args));
      }
    }
    const batchCount = Math.max(1, Number(args.count ?? 1));
    if (jsonPayload) {
      if (batchCount > 1) {
        if (!args["single-buy"]) {
          throw new Error(
            "批量下单请加上 --single-buy，避免对每笔订单自动进入监听支付流程",
          );
        }
        const result = await runBatchBuyFlow(
          host,
          finalToken,
          jsonPayload,
          args,
        );
        printResult(result, pretty);
        printBatchBuySummary(result);
        return;
      }
      if (shouldUseChainedBuyFlow(args)) {
        const result = await runBuyPaymentFlow(
          host,
          finalToken,
          jsonPayload,
          getBuyFlowOptions(args),
        );
        printBuyFlowResult(result, pretty);
        return;
      }
      const result = await createVipOrder(host, finalToken, jsonPayload);
      printSingleBuyResult(result, pretty);
      return;
    }

    const payload = buildBuyPayload(args, vipId);
    validateBuyPayload(payload);
    if (batchCount > 1) {
      if (!args["single-buy"]) {
        throw new Error(
          "批量下单请加上 --single-buy，避免对每笔订单自动进入监听支付流程",
        );
      }
      const result = await runBatchBuyFlow(host, finalToken, payload, args);
      printResult(result, pretty);
      printBatchBuySummary(result);
      return;
    }
    if (shouldUseChainedBuyFlow(args)) {
      const result = await runBuyPaymentFlow(
        host,
        finalToken,
        payload,
        getBuyFlowOptions(args),
      );
      printBuyFlowResult(result, pretty);
      return;
    }
    const result = await createVipOrder(host, finalToken, payload);
    printSingleBuyResult(result, pretty);
    return;
  }

  if (action === "batch") {
    if (!args["confirm-buy"]) {
      throw new Error("batch 操作默认拦截，请显式加上 --confirm-buy");
    }
    const finalToken = await ensureToken(
      host,
      token,
      args.account,
      args.password,
    );
    const vipSelection = await resolveVipId(host, finalToken, args["vip-id"]);
    const vipId = vipSelection.vipId;
    if (vipSelection.autoSelected) {
      console.error(
        `已自动选择默认套餐: vip_id=${vipId} (${vipSelection.plan?.title ?? "unknown"})`,
      );
    }
    if (!jsonPayload) {
      Object.assign(args, await resolveVipOrderContext(host, finalToken, args));
    }
    if (!jsonPayload && args["v-id"] && args.player && args.part) {
      console.error(
        `\n已自动带入最近播放记录: v_id=${args["v-id"]}, player=${args.player}, part=${args.part}`,
      );
    }
    if (!jsonPayload && (!args["v-id"] || !args.player || !args.part)) {
      if (process.stdin.isTTY || args["interactive-buy"]) {
        Object.assign(args, await promptVipOrderContext(args));
      }
    }

    const payload = jsonPayload ?? buildBuyPayload(args, vipId);
    if (!jsonPayload) {
      validateBuyPayload(payload);
    }

    const result = await runBatchCreateAndAutoPayFlow(
      host,
      finalToken,
      payload,
      args,
    );
    emitBatchProgressResult(args, result);
    printResult(result, pretty);
    printBatchCreateAndAutoPaySummary(result);
    return;
  }

  if (action === "autopay") {
    if (args["batch-file"]) {
      const result = await runBatchAutoPayFlow(args);
      printResult(result, pretty);
      printBatchAutoPaySummary(result);
    } else {
      const result = await runAutoPayFlow(args);
      printResult(result, pretty);
      printAutoPaySummary(result);
    }
    return;
  }

  if (action === "status") {
    const orderNo = String(args["order-no"] ?? "").trim();
    if (!orderNo) {
      throw new Error("status 需要 --order-no");
    }
    const timeoutMs = Number(args["timeout-ms"] ?? 15000);
    const finalToken = await ensureToken(
      host,
      token,
      args.account,
      args.password,
    );
    const result = await watchOrderStatus(host, orderNo, finalToken, timeoutMs);
    printResult(result, pretty);
    printOrderStatusSummary(result);
    return;
  }

  if (action === "login") {
    const loginArgs = jsonPayload ?? {
      type: args.type ?? "password",
      account: args.account,
      password: args.password,
    };

    if (!loginArgs || !loginArgs.type) {
      throw new Error("login 需要 --json 或至少提供 --type");
    }

    let payload = loginArgs;
    if (loginArgs.type === "password") {
      const credentials = getLoginCredentials(
        loginArgs.account,
        loginArgs.password,
      );
      const result = await runPasswordLogin(
        host,
        credentials.account,
        credentials.password,
      );
      const loginToken = extractLoginToken(result);
      if (loginToken) {
        cachedToken = loginToken;
      }
      printResult(result, pretty);
      if (loginToken) {
        console.error(`\nTOKEN: ${loginToken}`);
      }
      return;
    } else if (loginArgs.type === "vcode") {
      const { type, ...rest } = loginArgs;
      payload = rest;
    }

    const result = await sendEncryptedRequest({
      host,
      path:
        loginArgs.type === "vcode"
          ? "/pc/users/loginWithCode"
          : "/pc/users/login",
      method: "POST",
      data: payload,
    });
    printResult(result, pretty);
    const loginToken = extractLoginToken(result);
    if (loginToken) {
      console.error(`\nTOKEN: ${loginToken}`);
    }
    return;
  }

  if (action === "info") {
    const finalToken = await ensureToken(
      host,
      token,
      args.account,
      args.password,
    );
    const result = await sendEncryptedRequest({
      host,
      path: "/pc/users/info",
      method: "GET",
      token: finalToken,
    });
    printResult(result, pretty);
    return;
  }

  if (action === "raw") {
    const method = String(args.method ?? "GET").toUpperCase();
    const path = args.path;
    if (!path) {
      throw new Error("raw 需要 --path");
    }
    const result = await sendEncryptedRequest({
      host,
      path,
      method,
      data: jsonPayload ?? void 0,
      token,
    });
    printResult(result, pretty);
    return;
  }

  throw new Error(`未知 action: ${action}`);
}

run().catch((error) => {
  console.error("[test-vip] 失败:", error.message);
  process.exitCode = 1;
});
