cd "C:\\path\\to\\project\\location\\do_files"
local directory = "C:\\path\\to\\project\\location"

*Global name for log and tables
global regress = "baseline"
log using "..\\logs\\firm_year_regression_robust$regress.log", text replace

clear all
set more off
set matsize 11000
set maxvar 32767

* Baseline regression file
import delimited "`directory'\\mydata\\firm_patent_renewable50KM.csv", encoding(UTF-8) clear
* No multiple patent assignee regression file
// import delimited "`directory'\\mydata\\firm_patent_NOMULTIASSIGNEE50KM.csv", encoding(UTF-8) clear
* Placebo regression file
// import delimited "`directory'\\mydata\\firm_patent_PLACEBO50KM.csv", encoding(UTF-8) clear
* No manual patent assignee file
// import delimited "`directory'\\mydata\\firm_patent_NOMANUAL50KM.csv", encoding(UTF-8) clear

*Cleaning data
destring distance_km, replace force
replace distance_km = 9999 if missing(distance_km)

replace firm_city = firm_district if firm_city == "[]"

destring renewable_start_year, replace force

* UNCOMMENT FOR NO DENSE CITY SPECIFICATION
// local badcities "周口市 漯河市 阜阳市 广州市 厦门市 揭阳市 深圳市 郑州市 上海市 汕头市"
//
// gen byte drop_me = 0
// foreach c of local badcities {
//     replace drop_me = 1 if firm_city == "`c'"
// }
// drop if drop_me
* UNCOMMENT FOR NO DENSE CITY SPECIFICATION


gen renewable_open = (year >= renewable_start_year) if !missing(renewable_start_year)
replace renewable_open = 0 if missing(renewable_start_year)

local distance_cutoffs "0 1 3 5"  // change this for different size rings
local n_rings = wordcount("`distance_cutoffs'") - 1

* Build ring dummy variable for regression 
local ring_vars ""
forvalues r = 1/`n_rings' {
    local lower : word `r' of `distance_cutoffs'
    local upper : word `=`r'+1' of `distance_cutoffs'

    if `r' == 1 {
        gen within_ring_`r' = (distance_km >= `lower' & distance_km <= `upper') if !missing(distance_km)
    }
    else {
        gen within_ring_`r' = (distance_km > `lower' & distance_km <= `upper') if !missing(distance_km)
    }
    replace within_ring_`r' = 0 if missing(distance_km)
    gen open_ring_`r' = within_ring_`r' * renewable_open

    local ring_vars "`ring_vars' num_open_ring_`r'"
	* generate labels for the table
	if `lower' == 0 {
		local ring_coeflabels `"`ring_coeflabels' num_open_ring_`r' "Within `upper'km""'
	}
	else {
		local ring_coeflabels `"`ring_coeflabels' num_open_ring_`r' "Within `lower'-`upper'km""'
	}
}

* Keep firm characteristics
bysort firm_id year: gen obs_num = _n
preserve
keep if obs_num == 1

keep firm_name firm_id year sales_revenue capital firm_opening_year max_consecutive_years ///
     employees invention_patents utility_patents design_patents total_patents firm_city firm_district firm_code
tempfile firm_chars
save `firm_chars'
restore

* Collapse to firm-year level
local collapse_vars ""
forvalues r = 1/`n_rings' {
    local collapse_vars "`collapse_vars' num_renewables_within_ring_`r' = within_ring_`r' num_open_ring_`r' = open_ring_`r'"
}
collapse (sum) `collapse_vars', by(firm_id year)

merge 1:1 firm_id year using `firm_chars', nogen

gen firm_age = year - firm_opening_year

* IHS transformation of variable
gen asinh_sales     = asinh(sales_revenue)
gen asinh_capital   = asinh(capital)
gen asinh_employees = asinh(employees)
gen asinh_firm_age  = asinh(firm_age)

gen asinh_total_patents = asinh(total_patents)
gen asinh_invention     = asinh(invention_patents)
gen asinh_utility       = asinh(utility_patents)
gen asinh_design        = asinh(design_patents)

* Set number of digits in firm code (100 means two-digit)
gen firm_code_prefix = int(firm_code / 100)
tostring firm_code_prefix, gen(firm_code_prefix_str) format(%02.0f)

* some districts are same between firm, create city-district
encode firm_city, gen(city_id)
egen district_id = group(firm_city firm_district)

* City-year FE regression (total, invention, utility, design)
reghdfe asinh_total_patents `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year city_id#year) vce(cluster firm_id)
eststo m16
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local city_year_fe "Y"

reghdfe asinh_invention `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year city_id#year) vce(cluster firm_id)
eststo m17
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local city_year_fe "Y"

reghdfe asinh_utility `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year city_id#year) vce(cluster firm_id)
eststo m18
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local city_year_fe "Y"

reghdfe asinh_design `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year city_id#year) vce(cluster firm_id)
eststo m19
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local city_year_fe "Y"

* District-year FE regression (total, invention, utility, design)
reghdfe asinh_total_patents `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year district_id#year) vce(cluster firm_id)
eststo m20
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local district_year_fe "Y"

reghdfe asinh_invention `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year district_id#year) vce(cluster firm_id)
eststo m21
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local district_year_fe "Y"

reghdfe asinh_utility `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year district_id#year) vce(cluster firm_id)
eststo m22
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local district_year_fe "Y"

reghdfe asinh_design `ring_vars' ///
        asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
        absorb(firm_id firm_code_prefix#year district_id#year) vce(cluster firm_id)
eststo m23
estadd local controls "Y"
estadd local firm_fe "Y"
estadd local industry_year_fe "Y"
estadd local district_year_fe "Y"

* .tex table output
* City-year FE (baseline, nomulti, placebo)
esttab m16 m17 m18 m19 ///
    using "..\\tables\\asinh_city_$regress.tex", replace ///
    se b(%9.3f) se(%9.3f) star(* 0.10 ** 0.05 *** 0.01) ///
    keep(`ring_vars') order(`ring_vars') ///
    coeflabel(`ring_coeflabels') ///
    mtitles("Total" "Invention" "Utility" "Design") ///
    stats(N r2_a controls firm_fe industry_year_fe city_year_fe, ///
          labels("Observations" "Adj. R-squared" "Controls" "Firm FEs" ///
                 "Industry\$\times\$Year FEs" "City\$\times\$Year FEs") ///
          fmt(%9.0f %9.3f %s %s %s %s)) ///
    booktabs title("$regress") ///
    addnotes("Robust standard errors clustered at firm level" ///
             "Patents and firm characteristics use the inverse hyperbolic sine transformation")

* district-year FE (baseline, nomulti, placebo)
esttab m20 m21 m22 m23 ///
    using "..\\tables\\asinh_district_$regress.tex", replace ///
    se b(%9.3f) se(%9.3f) star(* 0.10 ** 0.05 *** 0.01) ///
    keep(`ring_vars') order(`ring_vars') ///
    coeflabel(`ring_coeflabels') ///
    mtitles("Total" "Invention" "Utility" "Design") ///
    stats(N r2_a controls firm_fe industry_year_fe district_year_fe, ///
          labels("Observations" "Adj. R-squared" "Controls" "Firm FEs" ///
                 "Industry\$\times\$Year FEs" "District\$\times\$Year FEs") ///
          fmt(%9.0f %9.3f %s %s %s %s)) ///
    booktabs title("$regress: District\$\times\$Year FE") ///
    addnotes("Robust standard errors clustered at firm level" ///
             "Patents and firm characteristics use the inverse hyperbolic sine transformation")
			 
			 
log close
