# Pre-registered pass/fail rule

Written and committed **before any model run**. The commit that adds this file
is the timestamp. It will not be edited after results exist. If the result
fails, it is reported as FAIL with its margin.

## Question

Can a graph whose link strengths live in HydraDB, and are refit every year,
nowcast the yearly change in **U.S. transportation-sector CO2** better than a
plain store can?

"Nowcast" means: at the end of year *t*, before EIA's annual CO2 and fuel
figures for *t* are final, estimate their change using inputs that are known
in near real time for year *t*: crude oil price, gasoline price, vehicle-miles
traveled and the electric share of new car registrations.

## Data (all U.S., annual, from the files listed in `data/manifest.json`)

| Node | Series id | Transform for year *t* |
|---|---|---|
| Crude | `us_crude_rac` (EIA MER 9.1, RACPUUS) | 100·ln(V_t / V_t-1) |
| Gasoline | `us_gasoline_unleaded` (EIA MER 9.4, RUUCUUS) | 100·ln(V_t / V_t-1) |
| VMT | `us_vmt` (FHWA VM-203 total) | 100·ln(V_t / V_t-1) |
| EVShare | `us_ev_share` (Ember, BEV+PHEV share of new registrations) | V_t − V_t-1 (percentage points) |
| FuelUse | `us_motor_gasoline_use` (EIA MER 3.7c, MGACPUS) | 100·ln(V_t / V_t-1) |
| CO2 | `us_transport_co2` (EIA MER 11.5, TEACEUS) | 100·ln(V_t / V_t-1) |

A value with any flag (provisional, partial, estimated, carried forward) is
treated as missing, as is any change that needs a missing value. Missing values
are never filled. EV share starts in 2011, so its change starts in 2012; before
that the EV input is absent.

## The graph (method)

Learned links are stored in HydraDB **as nodes** (edges are deduplicated on
source, target and type, so a link cannot be an edge with mutable weight):

- `Crude → Gasoline`
- `Gasoline → FuelUse`, `VMT → FuelUse`, `EVShare → FuelUse`
- `FuelUse → CO2`

Each target node (Gasoline, FuelUse, CO2) has a linear model: intercept plus
one weight per incoming link. Its weights live on the link nodes; its intercept
and the recursive-least-squares covariance live on a fit node for that target.

**Prediction for year *t*:**
1. FuelUse_hat = b_fuel + w_gas·Gasoline_t + w_vmt·VMT_t + w_ev·EVShare_t
   (an absent input contributes nothing).
2. CO2_hat = b_co2 + w_fuel·FuelUse_hat (two hops: the fuel figure is not
   known at nowcast time, so the predicted value is propagated).
3. Gasoline_hat = b_gas + w_crude·Crude_t is also predicted and scored as a
   secondary target. It does not feed the CO2 prediction, because the real
   gasoline price is known at nowcast time.

**Update after year *t*'s figures arrive:** each target's model is refit with
recursive least squares with forgetting factor λ, using the observed parent
values (observed FuelUse for the CO2 model). Only inputs present that year are
updated; absent ones keep their state. Start: weights 0, covariance 1000·I.
The new weights are written back to HydraDB before year *t*+1 is predicted, so
every correction changes the next prediction. A per-year history node of each
link's weight is also written.

## Baselines

- **No change:** predicted change = 0 (next level = this level).
- **Vector-store k-NN:** each past year is a vector of the same inputs
  (Crude, Gasoline, VMT, EVShare), standardised with the mean and standard
  deviation of the candidate pool. The query is year *t*'s vector. Distance is
  the root mean square difference over dimensions present in both vectors.
  Candidates are past years within a window of W years whose CO2 change is
  known. Prediction = mean CO2 change of the k nearest.
- **Frozen graph (ablation for continual learning):** the same graph, with the
  weights it had after its 2004 update, never refit again.
- **Direct regression (reported, not part of the rule):** one recursive least
  squares model from the four inputs straight to CO2, no intermediate node.

## Design and holdout periods

- Walk-forward runs every year from the first year with a CO2 change and all of
  Crude, Gasoline and VMT changes (1977).
- **Design period:** scored years 1982–2004 (1977–1981 are burn-in). All
  choices below are made on design-period MAE only.
  - λ for the graph and the direct model: one of {0.90, 0.95, 0.98, 1.00}.
  - k-NN: k in {3, 5, 7} and W in {10, 15, 20, all past years}.
  - Ties go to the larger λ, the larger k and the larger W.
- **Holdout period:** scored years 2005–2024, every year with an unflagged CO2
  change and present Crude, Gasoline and VMT changes. These years are used only
  for the final verdict.

## Metric

Mean absolute error (MAE) of the predicted CO2 change, in percentage points of
100·ln change, over the holdout years. n is reported. A paired bootstrap 95%
interval of each MAE difference (10,000 resamples, seed 20261116) is reported
but is not part of the rule.

## Rule: PASS only if all four hold

1. **Parity:** the HydraDB-backed run and an in-memory run of the same code give
   the same prediction for every year and every target, with maximum absolute
   difference ≤ 1e-9 percentage points.
2. **Beats no change:** graph holdout MAE ≤ 0.90 × no-change holdout MAE.
3. **Beats k-NN:** graph holdout MAE ≤ 0.90 × k-NN holdout MAE.
4. **Continual learning helps:** graph holdout MAE < frozen-graph holdout MAE.

Any one failing makes the verdict FAIL, reported with the margin for each part.
The rule, the grids, the periods and the metric will not be changed after the
first holdout run.

## Known limits of this test (stated in advance)

- n is small (about 20 holdout years); the bootstrap interval will be wide.
- The author knows the broad history of the holdout years (2008 recession,
  2020 pandemic) even though the method was tuned only on 1982–2004 data.
- Nowcasting is a narrow task: EIA publishes the real figures within months.
- The EV input exists only from 2012, so its link is learned only inside the
  holdout period, from very few points.
