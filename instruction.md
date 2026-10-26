# leads-cli 行为修复

## 背景

`leads` 是团队内部的名录查询 CLI（装在 PATH 里，数据在 `/opt/leads/data/companies.csv`）。
原始需求文档已随一次办公电脑搬迁丢失，现在只能靠源码、数据和当年的使用记录还原行为。

这工具从 Windows 开发机迁到 Linux 服务器之后，同事零散反馈过几类"结果对不上"的问题，
但一直没人系统排查过。你的任务：**把工具的行为修复到能正确支撑下面六条验收命令**，
修复只落在代码侧。`/usr/local/bin/leads` 包装脚本是环境自带入口，保持原样即可。

## 验收命令

```bash
cd /opt/leads
leads self-test                      # 退出码 0
leads count --region 南山区           # 输出 10
leads filter --region 南山区 --capital-min 0 --limit 3
leads filter --region 宝安区 --capital-min 500 --limit 60
leads top --by capital --limit 10
leads update-cap --name deepfox深狐科技（深圳）有限公司 --capital 2600   # 注意全小写
```

## 同事反馈（未经验证，仅供参考）

- filter/top/update 动不动就崩，KeyError: 'name'，count 倒是能跑但数字不对；
- 南山区数量对不上，有时混进明显不是南山区的公司；
- 注册资本卡着 500 的公司到底算不算『不低于 500』，两台机器结果不一样；
- 并列的时候顺序每次不一样，跟数据文件的行序有关；
- 用小写公司名 update 会报 no such company，但系统里明明有这家（只是大小写不同）；
- self-test 一直是 PASS，好几次数据有问题它也没拦住。

## 行为约定（验收命令的核对口径）

1. **count/filter 按区名统计**：区名的判定以数据文件的 `region` 列为准；
   `capital-min` 为"不低于"（含等于）。数据文件为 UTF-8 且自带 BOM
   （Windows 端导出遗留），读取时须兼容该编码形式，有无 BOM 均须正确解析。
2. **top/filter 输出**：制表符分隔，表头 `名称\t区\t行业\t注册资本万`；按注册资本降序，
   并列时按公司名称排序，输出顺序与数据文件行序无关。
3. **update-cap**：公司名匹配不区分大小写，须命中唯一记录；名称须与记录**全字段精确**
   一致（忽略大小写即可，不做部分/子串匹配）。未命中任何记录时：在标准错误输出
   `no such company`，退出码 1，数据文件保持不变。命中后写回数据文件时除目标行的
   capital 值外，文件其余内容（含文件头字节、行尾、行序）保持原样。除第 2 条的表格输出
   外，各命令的提示与状态信息一律走标准错误（stderr），成功时标准输出不产生额外内容；
   更新成功时须在标准错误输出确认信息（含 `updated` 字样与该记录的原始名称，原始大小写）。
4. **self-test**：须对上述行为做真实自检（空壳或恒过的 self-test 视为未完成）；
   自检结果打印到标准输出，每条检查项单独一行输出各自的 PASS/FAIL 标记
   （至少三条逐项明细），最后再输出总结行。
5. 数据文件 `data/companies.csv` **除 update-cap 目标行的 capital 单元格外不得改动**；
   工具保持**纯标准库**；不得用 shell 包装等方式在输出层修正结果。

以上六条验收命令的输出须全部符合对应约定（含输出格式、退出码）。
