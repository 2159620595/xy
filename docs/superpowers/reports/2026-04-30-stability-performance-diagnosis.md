# 首轮稳定性与性能诊断

## 范围

- `frontend/`
- `backend/Start.py`
- `backend/reply_server.py`
- `backend/judian/`
- `backend/netdisk/`

## 已确认的高优先问题

1. `frontend/src/api/judian.ts`
   - Judian 公共兑换与批量解锁接口直接使用裸 `axios`
   - 当前没有复用 `JUDIAN_API_TIMEOUT_MS`
   - 风险：公网请求在异常链路下可能长时间挂起，页面反馈慢

2. `frontend/src/utils/judian-auth.ts`
   - `verifyStoredJudianSession()` 和 `ensureJudianSession()` 直接使用裸 `fetch`
   - 当前没有显式超时控制
   - 风险：聚店会话校验或同步异常时会卡住调用链

3. `frontend/src/utils/netdisk-request.ts`
   - `ensureNetdiskSession()` 内部使用裸 `axios.post`
   - 当前没有显式 `timeout`
   - 风险：网盘会话引导在后端抖动时会长时间占用页面等待

## 暂不进入首轮实现的问题

- `backend/reply_server.py` 体积大，适合后续拆专项
- `backend/Start.py` 启动职责较多，但首轮不动启动流程
- 主后端和网盘后端已有局部缓存，不在没有运行证据的情况下盲改
- 前端包体仍有大块告警，但本轮先解决稳定性与请求超时，不混入包体专项

## 首轮落地项

1. 增加前端统一超时工具
2. 为 Judian 会话校验和会话同步补显式超时
3. 为 Netdisk 会话引导补显式超时
4. 为 Judian 公共接口切换到带超时的共享客户端

## 首轮已落地修复

1. 新增 `frontend/src/utils/http-timeout.ts`
   - 统一前端默认请求超时
   - 为 `fetch` 请求提供显式取消能力

2. 修复 `frontend/src/utils/judian-auth.ts`
   - 会话校验与会话同步现在有显式超时

3. 修复 `frontend/src/utils/netdisk-request.ts`
   - 网盘会话引导请求现在有显式超时
   - 网盘管理端和公开端客户端超时统一复用默认值

4. 修复 `frontend/src/api/judian.ts`
   - 聚店公共兑换与批量解锁接口改为复用共享客户端
   - 公共接口与鉴权接口超时配置一致

## 验证

- `npm run test -- src/utils/http-timeout.test.ts`
- `npm run test -- src/api/judian.test.ts`
- `npm run test -- src/utils/http-timeout.test.ts src/api/judian.test.ts`
- `npm run build`
