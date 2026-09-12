/**
 * 日程种子数据 - 浏览器控制台脚本
 *
 * 用法：打开 Tauri 应用的 DevTools (F12)，粘贴以下全部内容后回车。
 * 然后刷新页面即可看到大量日程数据。
 */

function seedScheduleItems() {
  const genId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  const base = new Date(2026, 6, 7, 8, 0, 0); // 2026-07-07 08:00
  const D = 86400000, H = 3600000;
  const t = (d, h, m = 0) => new Date(+base + d * D + h * H + m * 60000).toISOString();

  const items = [];

  // ── 今日 (2026-07-07 周二) ──
  items.push({ id: genId(), title: '与张伟案当事人会见', dateTime: t(0,9,0), endDateTime: t(0,10,30), type: 'meeting', completed: false, note: '讨论交通事故赔偿方案，确认调解意愿', createdAt: t(-3,14) });
  items.push({ id: genId(), title: '提交陈芳案代理词（最后期限）', dateTime: t(0,12,0), type: 'deadline', completed: false, note: '劳动仲裁案，中午前必须提交', createdAt: t(-5,9) });
  items.push({ id: genId(), title: '东城区法院调取证据', dateTime: t(0,14,0), endDateTime: t(0,16,0), type: 'appointment', completed: false, note: '调取王涛合同纠纷案工商登记信息', createdAt: t(-2,10) });
  items.push({ id: genId(), title: '团队案件讨论会', dateTime: t(0,16,30), endDateTime: t(0,17,30), type: 'meeting', completed: false, note: '讨论下周三个开庭案件的策略', createdAt: t(-1,9) });
  items.push({ id: genId(), title: '健身', dateTime: t(0,18,30), endDateTime: t(0,19,30), type: 'personal', completed: false, note: '律所楼下健身房', createdAt: t(-7,8) });

  // ── 本周 (7/8 周三 ~ 7/12 周日) ──
  items.push({ id: genId(), title: '李梅房产继承案调解', dateTime: t(1,9,30), endDateTime: t(1,11,0), type: 'court', completed: false, note: '朝阳区人民法院 第3调解室', createdAt: t(-10,11) });
  items.push({ id: genId(), title: '审查王刚案证据材料', dateTime: t(1,14,0), endDateTime: t(1,17,0), type: 'meeting', completed: false, note: '与助理一起梳理28份证据', createdAt: t(-4,16) });
  items.push({ id: genId(), title: '刘洋案二审上诉状截止', dateTime: t(2,17,0), type: 'deadline', completed: false, note: '一审判决后第15天，今天必须提交上诉状', createdAt: t(-20,10) });
  items.push({ id: genId(), title: '会见取保候审当事人赵强', dateTime: t(2,9,0), endDateTime: t(2,11,0), type: 'appointment', completed: false, note: '海淀区看守所，携带委托书和会见函', createdAt: t(-6,14) });
  items.push({ id: genId(), title: '律所合伙人会议', dateTime: t(3,10,0), endDateTime: t(3,12,0), type: 'meeting', completed: false, note: '讨论本季度营收目标和招聘计划', createdAt: t(-14,9) });
  items.push({ id: genId(), title: '宋氏继承纠纷案开庭', dateTime: t(3,14,0), endDateTime: t(3,17,0), type: 'court', completed: false, note: '西城区人民法院 第8法庭', createdAt: t(-30,9) });
  items.push({ id: genId(), title: '送检笔迹鉴定材料', dateTime: t(4,9,0), endDateTime: t(4,10,0), type: 'appointment', completed: false, note: '送往司法鉴定中心', createdAt: t(-3,15) });
  items.push({ id: genId(), title: '整理下周开庭材料', dateTime: t(4,14,0), endDateTime: t(4,18,0), type: 'personal', completed: false, note: '集中准备三个案件的开庭提纲', createdAt: t(-2,11) });
  items.push({ id: genId(), title: '周末值班电话咨询', dateTime: t(5,9,0), endDateTime: t(5,12,0), type: 'meeting', completed: false, note: '律所值班，处理来电咨询', createdAt: t(-7,8) });

  // ── 下周 (7/13 ~ 7/19) ──
  items.push({ id: genId(), title: '林达公司买卖合同纠纷开庭', dateTime: t(6,9,0), endDateTime: t(6,12,0), type: 'court', completed: false, note: '深圳市南山区人民法院 第5法庭', createdAt: t(-25,14) });
  items.push({ id: genId(), title: '公证处网页保全', dateTime: t(6,14,0), endDateTime: t(6,16,0), type: 'appointment', completed: false, note: '对侵权网页进行保全公证', createdAt: t(-8,10) });
  items.push({ id: genId(), title: '王磊诈骗案案情分析会', dateTime: t(7,10,0), endDateTime: t(7,12,0), type: 'meeting', completed: false, note: '与刑事部同事讨论辩护思路', createdAt: t(-4,16) });
  items.push({ id: genId(), title: '提交周敏案证据交换材料', dateTime: t(7,17,0), type: 'deadline', completed: false, note: '截止日，需提交证据目录及复印件', createdAt: t(-12,9) });
  items.push({ id: genId(), title: '顾问单位华兴科技法务回访', dateTime: t(8,9,30), endDateTime: t(8,11,30), type: 'meeting', completed: false, note: '审查新合同模板', createdAt: t(-5,11) });
  items.push({ id: genId(), title: '仲裁案庭前会议', dateTime: t(9,14,0), endDateTime: t(9,16,0), type: 'court', completed: false, note: '北京仲裁委员会 第2仲裁庭', createdAt: t(-15,13) });
  items.push({ id: genId(), title: '缴纳诉讼费截止', dateTime: t(10,17,0), type: 'deadline', completed: false, note: '华盛公司案诉讼费须今日前缴纳', createdAt: t(-18,9) });
  items.push({ id: genId(), title: '张老先生遗嘱拟写（上门）', dateTime: t(11,9,0), endDateTime: t(11,12,0), type: 'appointment', completed: false, note: '朝阳区上门服务', createdAt: t(-6,10) });
  items.push({ id: genId(), title: '知识产权讲座PPT准备', dateTime: t(11,14,0), endDateTime: t(11,17,0), type: 'personal', completed: false, note: '准备企业IP保护讲座', createdAt: t(-10,15) });
  items.push({ id: genId(), title: '亲子日——带孩子科技馆', dateTime: t(12,10,0), endDateTime: t(12,16,0), type: 'personal', completed: false, note: '', createdAt: t(-3,20) });

  // ── 更远日程 (7/20 ~ 8月) ──
  items.push({ id: genId(), title: '黄某人身损害赔偿案开庭', dateTime: t(13,9,0), endDateTime: t(13,12,0), type: 'court', completed: false, note: '海淀区人民法院 第12法庭', createdAt: t(-20,11) });
  items.push({ id: genId(), title: '公司并购尽调汇报', dateTime: t(14,10,0), endDateTime: t(14,12,0), type: 'meeting', completed: false, note: '向客户汇报5项法律风险', createdAt: t(-9,14) });
  items.push({ id: genId(), title: '提交质证意见截止', dateTime: t(15,17,0), type: 'deadline', completed: false, note: '针对对方12份证据的书面质证意见', createdAt: t(-7,10) });
  items.push({ id: genId(), title: '赴天津调取工商档案', dateTime: t(16,8,0), endDateTime: t(16,17,0), type: 'appointment', completed: false, note: '查对方公司变更记录', createdAt: t(-11,9) });
  items.push({ id: genId(), title: '建设工程合同纠纷鉴定质证', dateTime: t(18,9,0), endDateTime: t(18,12,0), type: 'court', completed: false, note: '丰台区人民法院 第6法庭', createdAt: t(-30,10) });
  items.push({ id: genId(), title: '律所团建——怀柔青龙湖', dateTime: t(19,8,0), endDateTime: t(19,18,0), type: 'personal', completed: false, note: '漂流+烧烤', createdAt: t(-14,9) });
  items.push({ id: genId(), title: '涉外案件研讨会（远程）', dateTime: t(21,14,0), endDateTime: t(21,16,0), type: 'meeting', completed: false, note: 'Zoom 与香港联营所讨论跨境执行', createdAt: t(-10,11) });
  items.push({ id: genId(), title: '陈某某受贿罪一审开庭', dateTime: t(24,9,0), endDateTime: t(24,17,0), type: 'court', completed: false, note: '北京市一中院 第3法庭，预计全天', createdAt: t(-40,9) });
  items.push({ id: genId(), title: '年中工作总结报告提交', dateTime: t(26,18,0), type: 'deadline', completed: false, note: '向管委会提交上半年总结', createdAt: t(-5,14) });
  items.push({ id: genId(), title: '法律援助中心值班', dateTime: t(28,9,0), endDateTime: t(28,17,0), type: 'appointment', completed: false, note: '东城区法律援助中心', createdAt: t(-20,8) });

  // ── 已完成的（测试已完成状态） ──
  items.push({ id: genId(), title: '赵某欠款纠纷案开庭', dateTime: t(-2,9,0), endDateTime: t(-2,11,0), type: 'court', completed: true, note: '对方同意调解', createdAt: t(-20,10) });
  items.push({ id: genId(), title: '提交管辖权异议申请书', dateTime: t(-3,17,0), type: 'deadline', completed: true, note: '已按时提交', createdAt: t(-10,9) });
  items.push({ id: genId(), title: '与审计师对接财务数据', dateTime: t(-4,14,0), endDateTime: t(-4,16,0), type: 'appointment', completed: true, note: '已完成数据交接', createdAt: t(-8,11) });
  items.push({ id: genId(), title: '新人合同审查培训', dateTime: t(-5,10,0), endDateTime: t(-5,12,0), type: 'meeting', completed: true, note: '给新入职律师助理培训', createdAt: t(-12,9) });
  items.push({ id: genId(), title: '年度体检', dateTime: t(-7,8,0), endDateTime: t(-7,12,0), type: 'personal', completed: true, note: '', createdAt: t(-30,9) });

  // ── 多日跨越 ──
  items.push({ id: genId(), title: '上海出差——调查取证', dateTime: t(20,8,0), endDateTime: t(22,18,0), type: 'appointment', completed: false, note: '浦东新区法院、工商局调证', createdAt: t(-15,14) });
  items.push({ id: genId(), title: '破产管理人会议（3天）', dateTime: t(30,9,0), endDateTime: t(32,17,0), type: 'meeting', completed: false, note: '房地产公司破产清算案', createdAt: t(-20,10) });
  items.push({ id: genId(), title: '全天撰写并购法律意见书', dateTime: t(23,8,0), endDateTime: t(23,19,0), type: 'personal', completed: false, note: '客户催得急', createdAt: t(-3,17) });
  items.push({ id: genId(), title: '全市律师业务培训（全天）', dateTime: t(27,8,0), endDateTime: t(27,18,0), type: 'meeting', completed: false, note: '市律协年度继续教育', createdAt: t(-25,9) });

  localStorage.setItem('lawclaw_schedule', JSON.stringify(items));
  console.log('✅ 已写入 ' + items.length + ' 条日程数据到 localStorage');
  console.log('📋 现在刷新页面即可看到效果 → Cmd/Ctrl + R');
}

seedScheduleItems();
