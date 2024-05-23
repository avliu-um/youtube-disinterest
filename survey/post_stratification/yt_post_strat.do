use "/PATH/TO/burst/survey/post_stratification/sex_age_20.dta"
svyset _n, fpc(n_pop) poststrata(type) postweight(n_type)

svy: mean delete_aware
svy: mean dislike_aware
svy: mean not_int_aware
svy: mean no_chan_aware
svy: mean delete_aware__exp
svy: mean dislike_aware__exp
svy: mean not_int_aware__exp
svy: mean no_chan_aware__exp
svy: mean delete_use__exp_aware
svy: mean dislike_use__exp_aware
svy: mean not_int_use__exp_aware
svy: mean no_chan_use__exp_aware
svy: mean delete_eff__exp_aware
svy: mean dislike_eff__exp_aware
svy: mean not_int_eff__exp_aware
svy: mean no_chan_eff__exp_aware
svy: mean delete_eff__exp_aware_use
svy: mean dislike_eff__exp_aware_use
svy: mean not_int_eff__exp_aware_use
svy: mean no_chan_eff__exp_aware_use
svy: mean delete_eff__exp_aware_no_use
svy: mean dislike_eff__exp_aware_no_use
svy: mean not_int_eff__exp_aware_no_use
svy: mean no_chan_eff__exp_aware_no_use
