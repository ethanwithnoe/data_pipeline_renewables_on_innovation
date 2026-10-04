cd "C:\\path\\to\\project\\location\\do_files"
local directory = "C:\\path\\to\\project\\location"

clear all
use "`directory'\ASIE_data\工业企业数据2013.dta", clear

log using filter_NONrenewable_firms.log, text replace

sort 行业小类代码
count if 行业小类代码 == "3411"
count if 行业小类代码 == "3412"
count if 行业小类代码 == "3413"

preserve

keep if 开业成立时间年 >= "2000"
sort 开业成立时间年

keep if inlist(行业小类代码, "3411", "3412", "3413")

keep 组织机构代码 企业名称 省自治区直辖市 地区市州盟 县区市旗 街道办事处 详细地址 邮政编码 开业成立时间年 行业小类代码 主要业务活动或主要产品1 主要业务活动或主要产品2 主要业务活动或主要产品3
tempfile OnlyNONRENEWABLE2013

destring 开业成立时间年, replace
save "`directory'\mydata\ASIE_NONrenewableFirms2000-2013.dta", replace
export delimited "`directory'\mydata\ASIE_NONrenewableFirms2000-2013.csv", replace

restore

log close
