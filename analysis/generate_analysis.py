"""Reproducible offline evaluation of AquaGent (scenarios + sensitivity sweeps).

Run from the repository root:  python analysis/generate_analysis.py
Writes CSV files to analysis/data/ and quick-look PNG charts to analysis/figures/.
Uses the project's own functions in src/; it does not change the app.
"""
from pathlib import Path
import sys, csv
from dataclasses import replace
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT))
from src.model import Inputs, fog_water_liters, mof_water_liters
from src.decision import evaluate
from experiments.run_simulation import CASES

OUT=ROOT/'data'; FIG=ROOT/'figures'; OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':11,'axes.titlesize':14,'figure.dpi':120})
def save(filename):
    plt.tight_layout(); plt.savefig(FIG/filename,dpi=190,bbox_inches='tight'); plt.close()

rows=[]
for name,kwargs in CASES:
    r=evaluate(Inputs(**kwargs)); p=r.get('recommended') or {}
    rows.append({'Scenario':name,'Status':r['status'],'P(fog)':r['fog_probability'],
                 'Recommendation':p.get('method','None'),'Hours':p.get('hours',''),
                 'Water (L), demo':p.get('water_liters_demo',''),
                 'Energy (kWh), demo':p.get('energy_kwh_demo',''),
                 'Score, demo':p.get('score_demo',''),
                 'Warnings':' | '.join(r['warnings'])})
with (OUT/'scenario_results.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

# Baseline is explicit: selected humid/fog/energy scenario; results may differ from older user screenshot.
base=Inputs(humidity=85,temperature_c=22,fog_observed=True,energy_budget_kwh=8,
            max_hours=4,wind_m_s=2,mesh_area_m2=2,mesh_efficiency=.30,fog_lwc_g_m3=.20,mof_mass_kg=1)
post=evaluate(base)['fog_probability']

# Figure 1 scenario outcomes
names=[r['Scenario'] for r in rows]
waters=[float(r['Water (L), demo']) if r['Water (L), demo']!='' else 0 for r in rows]
fig,ax=plt.subplots(figsize=(11,5.2)); bars=ax.bar(range(len(names)),waters)
ax.set_xticks(range(len(names)),names,rotation=35,ha='right');ax.set_ylabel('Estimated collection (L; demo)')
ax.set_title('Figure 1. Simulated water output across 10 scenarios')
for i,(bar,r) in enumerate(zip(bars,rows)):
    if r['Status']!='SUCCESS':
        ax.annotate(r['Status'].replace('NO_FEASIBLE_METHOD','No plan').replace('SENSOR_WARNING','Input warning'),
            (i,0),xytext=(0,5),textcoords='offset points',rotation=90,ha='center',va='bottom',fontsize=7)
save('fig1_scenarios.png')

# Figure 2 wind versus fog yield; change one parameter holding others constant.
winds=np.linspace(0,6,61)
wy=[fog_water_liters(replace(base,wind_m_s=float(x)),4,post) for x in winds]
fig,ax=plt.subplots(figsize=(8,4.8));ax.plot(winds,wy,linewidth=2);ax.set(xlabel='Wind speed (m/s)',ylabel='Expected fog-mesh yield (L; demo)',title='Figure 2. Fog output sensitivity to wind speed')
ax.grid(alpha=.25);save('fig2_fog_wind.png')

# Figure 3 LWC sensitivity
lwcs=np.linspace(0,0.5,51)
ly=[fog_water_liters(replace(base,fog_lwc_g_m3=float(x)),4,post) for x in lwcs]
fig,ax=plt.subplots(figsize=(8,4.8));ax.plot(lwcs,ly,linewidth=2);ax.set(xlabel='Assumed fog LWC (g/m³)',ylabel='Expected fog-mesh yield (L; demo)',title='Figure 3. Fog output sensitivity to liquid-water content')
ax.grid(alpha=.25);save('fig3_fog_lwc.png')

# Figure 4 MOF mass: reference pro-rata rate
masses=np.linspace(.5,5,46)
my=[mof_water_liters(replace(base,mof_mass_kg=float(x)),4) for x in masses]
fig,ax=plt.subplots(figsize=(8,4.8));ax.plot(masses,my,linewidth=2);ax.set(xlabel='MOF-303 sorbent mass (kg)',ylabel='Illustrative MOF water yield (L in 4h; demo)',title='Figure 4. MOF-303 reference yield vs sorbent mass')
ax.grid(alpha=.25);save('fig4_mof_mass.png')

# Figure 5 crucial limitation: fixed MOF at all nonzero RH
rh_vals=np.arange(5,101,5)
rh_out=[mof_water_liters(replace(base,humidity=float(h)),4) for h in rh_vals]
fig,ax=plt.subplots(figsize=(8,4.8));ax.plot(rh_vals,rh_out,marker='o',markersize=3);ax.set(xlabel='Relative humidity (%)',ylabel='Illustrative MOF output (L in 4h)',title='Figure 5. Model limitation: MOF yield is insensitive to RH')
ax.set_ylim(0,.05);ax.grid(alpha=.25);save('fig5_mof_humidity_limitation.png')

# Figure 6 energy budget: selection, durations (discontinuous, not yield curves)
budgets=[.0,.1,.2,.3,.4,.6,.8,1.,1.5,2.,3.,5.,8.]
energy_rows=[]
for budget in budgets:
    r=evaluate(replace(base,energy_budget_kwh=float(budget)))
    p=r['recommended'] or {}
    energy_rows.append({'Available energy (kWh)':budget,'Status':r['status'],
                        'Method':p.get('method','None'),'Hours':p.get('hours',''),
                        'Water (L), demo':p.get('water_liters_demo',''),
                        'Energy used (kWh), demo':p.get('energy_kwh_demo','')})
with (OUT/'energy_budget_sensitivity.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=energy_rows[0].keys());w.writeheader();w.writerows(energy_rows)
fig,ax=plt.subplots(figsize=(9,4.7));ax.step(budgets,[float(r['Water (L), demo']) if r['Water (L), demo']!='' else 0 for r in energy_rows],where='post',marker='o')
ax.set(xlabel='Available demo energy budget (kWh)',ylabel='Selected-plan water (L; demo)',title='Figure 6. Decision sensitivity to energy budget')
ax.grid(alpha=.25);save('fig6_energy_budget.png')

with (OUT/'sensitivity_values.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['variable','input','yield_liters_demo','fixed_conditions'])
    for x,y in zip(winds,wy):w.writerow(['wind_m_s',round(x,3),y,'fog 4h; baseline except wind'])
    for x,y in zip(lwcs,ly):w.writerow(['fog_lwc_g_m3',round(x,4),y,'fog 4h; baseline except LWC'])
    for x,y in zip(masses,my):w.writerow(['mof_mass_kg',round(x,3),y,'MOF 4h; baseline except mass'])
    for x,y in zip(rh_vals,rh_out):w.writerow(['humidity_pct',int(x),y,'MOF 4h; baseline except RH'])

success=sum(r['Status']=='SUCCESS' for r in rows)
none=sum(r['Status']=='NO_FEASIBLE_METHOD' for r in rows)
warn=sum(r['Status']=='SENSOR_WARNING' for r in rows)
print('COUNTS',success,none,warn,'PFOG',post)
for r in rows:print(r['Scenario'],r['Status'],r['Recommendation'],r['Water (L), demo'],r['Energy (kWh), demo'])
print('Baseline wind 2',fog_water_liters(base,4,post),'MOF baseline',mof_water_liters(base,4))
print('Sensitivity wind 1/2/4',[(x,fog_water_liters(replace(base,wind_m_s=x),4,post)) for x in [1,2,4]])
print('Sensitivity LWC .1/.2/.4',[(x,fog_water_liters(replace(base,fog_lwc_g_m3=x),4,post)) for x in [.1,.2,.4]])
print('Mass 1/2/4',[(x,mof_water_liters(replace(base,mof_mass_kg=x),4)) for x in [1,2,4]])
print('ENERGY',energy_rows)
