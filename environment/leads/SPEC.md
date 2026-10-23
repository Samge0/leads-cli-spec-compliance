# leads SPEC · 名录查询工具需求规格 v1.2

> 本文件是 leads 工具的唯一行为基准。工具的任何行为与本文不符，均视为缺陷。

## 1. 数据

- 数据文件：`data/companies.csv`，UTF-8（**有无 BOM 均必须正确解析**——文件由 Windows
  端工具导出，历史上一直带 BOM），含表头：`name,region,address,trade,capital_wan`
- `capital_wan` 为注册资本，单位：万元，非负整数
- 数据文件**只读**；`--update-cap` 是唯一允许改写数据文件的操作（见 §5）

## 2. 子命令与参数

```
leads filter --region <区名> --capital-min <万元> [--trade <行业>] --limit <N>
leads top --by capital --limit <N>
leads count --region <区名>
leads update-cap --name <公司全名> --capital <万元>
leads self-test
```

- `--trade` 缺省 = 不过滤行业
- `--limit` 必填（filter/top）；`N` 为正整数

## 3. 匹配语义（最重要的一节）

- **region**：必须与 `region` **列精确相等**（整串比对）。不允许按 address 子串
  推断区域——地址写法不可靠（有跨区地址、有不含区名的地址）。
- **capital-min**：语义为「注册资本**不低于**该值」，即 `>=`。恰好等于阈值的数据
  行必须计入。
- **name / --name**：大小写**不敏感**匹配（"deepfox..." 与 "DeepFox..." 视为同名）。
- **--trade**：与 `trade` 列精确相等。

## 4. 输出与排序

- 所有列表输出：**注册资本降序**；并列时按**名称字典序升序**作为次键。
  两级排序键都不允许依赖输入文件行序（行序不可靠）。
- `top`：全库按同一排序规则取前 N 行，输出列与 filter 相同。
- `filter`/`top` 输出为制表符分隔：`名称<TAB>区<TAB>行业<TAB>注册资本万`，第一行
  为表头行 `名称	区	行业	注册资本万`。
- `count` 只输出一个整数（命中行数），无表头。
- 输出到 stdout；其余信息（错误、提示）一律走 stderr。

## 5. update-cap

- 按名称（大小写不敏感）精确匹配**唯一**一条记录，把 `capital_wan` 改为新值。
- 匹配到 0 条：stderr 报 `no such company`，退出码 1；不改文件。
- CSV 其余字段、行序、BOM 有无**保持原样**（只允许修改目标行的 capital 单元格）。

## 6. self-test

- 工具自带的自检子命令：对内置断言（BOM 解析、region 精确匹配、>= 边界、排序稳
  定性）逐项自检，全部通过退出码 0，否则非 0。
- 该子命令**不得修改**数据文件。

## 7. 退出码

- 成功 0；用法错误 2；运行期错误 1。
