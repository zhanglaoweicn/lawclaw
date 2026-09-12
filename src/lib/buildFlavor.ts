/**
 * 构建风味（build flavor）——同一套代码产出两种交付物：
 *
 * - `demo`（默认）：首启自动灌入演示案件数据，供当面/远程给客户演示。
 * - `clean`：首启为空台账、不含任何演示数据与密钥，交付客户自行建档。
 *
 * 由构建时注入：`VITE_LAWCLAW_FLAVOR=demo|clean`（见 scripts/build_release.py）。
 * 未注入时按 demo 处理，保持开发与既有行为不变。
 */
export type BuildFlavor = 'demo' | 'clean'

function resolveFlavor(): BuildFlavor {
  const raw = (import.meta.env.VITE_LAWCLAW_FLAVOR as string | undefined)?.trim().toLowerCase()
  return raw === 'clean' ? 'clean' : 'demo'
}

export const BUILD_FLAVOR: BuildFlavor = resolveFlavor()

/** 演示构建：带演示数据，并保留「重置演示数据」入口 */
export const isDemoBuild = BUILD_FLAVOR === 'demo'
