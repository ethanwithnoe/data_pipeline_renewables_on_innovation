cd "C:\\path\\to\\project\\location\\do_files"
local directory = "C:\\path\\to\\project\\location"

clear all

use "`directory'\ASIE_data\工业企业数据2013.dta", clear

log using filter_renewable_firms.log, text replace

sort 行业小类代码

count if 行业小类代码 == "3825"
count if 行业小类代码 == "3415"
count if 行业小类代码 == "3414"

preserve

keep if 开业成立时间年 >= "2000"
sort 开业成立时间年

keep if inlist(行业小类代码, "3825", "3415", "3414")

keep 组织机构代码 企业名称 省自治区直辖市 地区市州盟 县区市旗 街道办事处 详细地址 邮政编码 开业成立时间年 行业小类代码 主要业务活动或主要产品1 主要业务活动或主要产品2 主要业务活动或主要产品3
tempfile OnlySolarPanels2013

destring 开业成立时间年, replace
save "`directory'\mydata\ASIE_Renewables_Firms_2000-2013.dta", replace
export delimited "`directory'\mydata\ASIE_Renewables_Firms_2000-2013.csv", replace

restore

use "`directory'\mydata\ASIE_Renewables_Firms_2000-2013.dta", clear

destring 行业小类代码, replace

label define indlbl 3414 "Water Turbine Firms" 3415 "Wind Turbine Firms" 3825 "Photovoltaic Cell Firms"
label values 行业小类代码 indlbl

graph bar (count), over(行业小类代码) over(开业成立时间年) asyvars stack ///
    ytitle("Number of Firms")
	
	
graph export "`directory'\figures\RenewableOpeningsByYear2000-2013.png", replace
graph save "`directory'\figures\RenewableOpeningsByYear2000-2013.gph", replace

log close
