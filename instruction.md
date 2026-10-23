# leads-cli 规格符合性修复

## 背景

`leads` 是团队内部的名录查询 CLI（装在 PATH 里，数据在 `/opt/leads/data/companies.csv`）。
它的行为基准只有一份：`/opt/leads/SPEC.md`（需求规格 v1.2）。

这工具从 Windows 开发机迁移到 Linux 服务器后，同事陆续反馈过几类"结果对不上"的问题，
但一直没人对照 SPEC 系统排查。你的任务：**以 SPEC 为唯一基准，找出工具行为与规格的
全部偏离并修复**，使以下验收命令的输出与 SPEC 完全一致：

```bash
cd /opt/leads
leads self-test                      # 退出码 0
leads count --region 南山区           # 输出 10
leads filter --region 南山区 --capital-min 0 --limit 3
leads filter --region 宝安区 --capital-min 500 --limit 60
leads top --by capital --limit 10
leads update-cap --name deepfox深狐科技（深圳）有限公司 --capital 2600   # 注意全小写
```

## 已知线索（来自同事反馈，未经验证）

- 「filter/top/update 动不动就崩，KeyError: 'name'，count 倒是能跑但数字不对」；
- 「南山区数量对不上，有时混进明显不是南山区的公司」；
- 「注册资本卡着 500 的公司到底算不算『不低于 500』，两台机器结果不一样」；
- 「并列的时候顺序每次不一样，跟数据文件的行序有关」；
- 「用小写公司名 update 会报 no such company，但系统里明明有这家（只是大小写不同）」。

## 约束

1. 数据文件 `data/companies.csv` 中**除 update-cap 目标行的 capital 单元格外，
   不得修改/增删任何内容**（行序、其他字段、BOM 有无均保持原样）；
2. `SPEC.md` 是需求基准，**不得修改**；
3. 工具保持**纯标准库**（不得引入第三方依赖）；
4. 修复必须落在 `leads_cli.py`（或你新建的、被它调用的模块）里，不得用 shell 包一层
   后处理输出的方式"修正"结果；
5. `self-test` 子命令要能反映修复后的真实行为（空壳或恒过的 self-test 视为未完成）。

## 验收口径

- 上述全部命令行为与 SPEC 一致（匹配语义、边界、排序、输出格式、退出码）；
- `update-cap` 用小写名字能命中唯一记录，写回后其他行原样；
- 判分脚本将在当前状态上直接执行，无需重启任何服务。
