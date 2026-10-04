cd "C:\\path\\to\\project\\location\\do_files"
local directory = "C:\\path\\to\\project\\location"

global ring_distance = 1

*Global name for log and tables
global regress = "baseline"

log using "..\\logs\\event_study_utility_patent$ring_distance$regress.log", text replace

clear all
set more off
set matsize 11000
set maxvar 32767

import delimited "`directory'\\mydata\\firm_patent_renewable50KM.csv", encoding(UTF-8) clear

*Cleaning data
destring distance_km, replace force
replace distance_km = 9999 if missing(distance_km)

destring renewable_start_year, replace force

* generate dummy variable for post
gen renewable_open = (year >= renewable_start_year) if !missing(renewable_start_year)
replace renewable_open = 0 if missing(renewable_start_year)

* generate dummy variable for ring
gen within_ring = (distance_km <= $ring_distance) if !missing(distance_km)
replace within_ring = 0 if missing(distance_km)

*has to be both open and within the ring
gen open_ring = within_ring * renewable_open

gen within_5 = (distance_km <= 5)

* keep firm characteristics
bysort firm_id year: gen obs_num = _n
preserve
keep if obs_num == 1
keep firm_name firm_id year sales_revenue capital firm_opening_year max_consecutive_years ///
     employees invention_patents utility_patents design_patents total_patents firm_city firm_district firm_code
tempfile firm_chars
save `firm_chars'
restore

* Collapse to firm-year level
collapse (sum) num_renewables_within_ring = within_ring ///
              num_open_ring = open_ring ///
              num_within5 = within_5, ///
         by(firm_id year)

* Merge back firm characteristics
merge 1:1 firm_id year using `firm_chars', nogen

gen firm_age = year - firm_opening_year

gen asinh_num_open_ring = asinh(num_open_ring)

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

replace firm_city = firm_district if firm_city == "[]"

encode firm_city, gen(city_id)
egen district_id = group(firm_city firm_district)

* EVENT STUDY

sort firm_id year

* firm is first treated if there is at least one renwable firm open and close that year and is the previous year has 0 renewable firms
* firms already treated in 2000 are dropped
bysort firm_id (year): gen temp_first_treat = year if num_open_ring > 0 & num_open_ring[_n-1] == 0
bysort firm_id (year): egen first_treat_year = min(temp_first_treat)

* make the event time the number of years relative to treatment
gen event_time = year - first_treat_year

preserve

* controls are firms which are 5 km or further of any renewable firm
bysort firm_id: egen max_within5 = max(num_within5)
gen never_within5 = (max_within5 == 0)

* keep all within 1 km firms, and drop 1-5km firms
keep if !missing(first_treat_year) | never_within5 == 1

* controls get event time 0
replace event_time = 0 if never_within5 == 1

eventdd asinh_utility asinh_sales asinh_capital asinh_employees asinh_firm_age, ///
    timevar(event_time) ///
    baseline(-1) ///
    accum ///
    lags(7) ///
    leads(7) ///
	hdfe ///
    cluster(firm_id) ///
    absorb(firm_id firm_code_prefix#year city_id#year) ///
    graph_op(xlabel(-7(1)7) scheme(s2mono) ///
             ytitle("Utility Patenting (IHS)", size(*1.3)) ///
             xtitle("Years Relative To Renewable Energy Firm Opening", size(*1.3)) ///
			 legend(off) ///
             graphregion(fcolor(white) color(white)) ///
             plotregion(fcolor(white)) ///
             bgcolor(white) ///
             xsize(7) ysize(4))

graph export "`directory'\\figures\\event_study_asinh_utility_patents_$ring_distance$regress.png", ///
    replace width(2000)

test lead2 lead3 lead4 lead5 lead6 lead7
	
restore

log close

