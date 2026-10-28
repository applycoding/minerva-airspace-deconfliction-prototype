"""Independent sampling and radio reference calculations for simulation evidence."""
import math
import numpy as np


def _legs(waypoints, buffer):
    points = [(w.epoch_s,np.array([w.x_m,w.y_m,w.alt_m],dtype=float)) for w in waypoints]
    if buffer:
        points = [(points[0][0]-buffer,points[0][1])]+points+[(points[-1][0]+buffer,points[-1][1])]
    return list(zip(points,points[1:]))


def sample_space_time(waypoints_a, waypoints_b, h_sep_m=100., v_sep_m=30., time_buf_s=15.):
    """Return hit, sampled minima, sample count and largest relative step distance."""
    hit = False
    min_h = min_v = math.inf
    samples = 0
    max_step = 0.
    for (ta,pa),(tb,pb) in _legs(waypoints_a,time_buf_s):
        va = (pb-pa)/(tb-ta)
        for (tc,pc),(td,pd) in _legs(waypoints_b,time_buf_s):
            start,end = max(ta,tc),min(tb,td)
            if start > end:
                continue
            vb = (pd-pc)/(td-tc)
            speed = float(np.linalg.norm(va-vb))
            dt = min(.1,1./max(speed,1.))
            intervals = max(1,math.ceil((end-start)/dt))
            max_step = max(max_step,speed*(end-start)/intervals)
            # Bounded chunks keep fast encounters from allocating unbounded arrays.
            for first in range(0,intervals+1,100000):
                times = start+np.arange(first,min(intervals+1,first+100000))*(end-start)/intervals
                delta = (pa+(times-ta)[:,None]*va)-(pc+(times-tc)[:,None]*vb)
                horizontal = np.hypot(delta[:,0],delta[:,1]); vertical = np.abs(delta[:,2])
                hit = hit or bool(np.any((horizontal < h_sep_m-1e-9)&(vertical < v_sep_m-1e-9)))
                min_h = min(min_h,float(horizontal.min())); min_v = min(min_v,float(vertical.min()))
                samples += len(times)
    return dict(hit=hit,min_horiz_m=min_h,min_vert_m=min_v,samples=samples,max_relative_step_m=max_step)


def evaluate_radio(plan_a, plan_b):
    """Direction-specific powers and flags, derived without production helpers."""
    a,b = plan_a.radio,plan_b.radio
    low = max(plan_a.waypoints[0].epoch_s,plan_b.waypoints[0].epoch_s)
    high = min(plan_a.waypoints[-1].epoch_s,plan_b.waypoints[-1].epoch_s)
    band = abs(a.freq_mhz-b.freq_mhz) < a.bw_mhz/2+b.bw_mhz/2+max(a.guard_mhz,b.guard_mhz)
    results = []
    for transmitter,receiver in ((plan_a,plan_b),(plan_b,plan_a)):
        if low > high or not band:
            results.append(dict(tx_id=transmitter.plan_id,rx_id=receiver.plan_id,hit=False,power_dbm=None))
            continue
        best_squared = math.inf
        for first,last in zip(transmitter.waypoints,transmitter.waypoints[1:]):
            left,right = max(low,first.epoch_s),min(high,last.epoch_s)
            if left > right:
                continue
            duration = last.epoch_s-first.epoch_s
            origin = [first.x_m-receiver.radio.gcs_x_m,first.y_m-receiver.radio.gcs_y_m,first.alt_m-2.]
            velocity = [(last.x_m-first.x_m)/duration,(last.y_m-first.y_m)/duration,(last.alt_m-first.alt_m)/duration]
            denominator = sum(component**2 for component in velocity)
            offset = -sum(origin[k]*velocity[k] for k in range(3))/denominator if denominator else 0.
            offset = max(left-first.epoch_s,min(right-first.epoch_s,offset))
            best_squared = min(best_squared,sum((origin[k]+offset*velocity[k])**2 for k in range(3)))
        kilometres = math.sqrt(max(100.,best_squared))/1000
        loss = 32.44+20*math.log10(kilometres*transmitter.radio.freq_mhz)
        power = transmitter.radio.tx_power_dbm+transmitter.radio.tx_gain_dbi+receiver.radio.rx_gain_dbi-loss
        results.append(dict(tx_id=transmitter.plan_id,rx_id=receiver.plan_id,hit=power > receiver.radio.rx_threshold_dbm+1e-9,power_dbm=power))
    return results
