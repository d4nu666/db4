ref_temp = 18
ref_od = 1

sample_input = [16, 17, 18, 19, 18, 18, 19, 17, 18, 19, 17, 18, 18, 19, 18, 19, 20, 18,
                19, 17, 16, 17, 16, 17, 17, 18, 19, 19, 19, 19, 18]

kp, ki, kd = 1, 0.5, 0.5
wait_seconds = 1

def mussel_system():
    intT = 0.0
    errorT = 0.0
    intOD = 0.0
    errorOD = 0.0
    while True:
        intT, errorT, control_signal_temp, temp = pid_temp(intT, errorT)
        cooler_pump(control_signal_temp)

        intOD, errorOD, control_signal_OD, od = pid_od(intOD, errorOD)
        algae_pump(control_signal_OD)

        serverUpload(temp, control_signal_temp, od, control_signal_OD)
        wait(wait_seconds)


def pid_temp(integral, prev_err):
    temp = read_temperature()
    error = ref_temp - temp
    integral += error * wait_seconds
    pterm = kp * error
    iterm = ki * integral
    dterm = kd * (error - prev_err) / wait_seconds
    control_signal = pterm + dterm + iterm
    return integral, error, control_signal, temp

def pid_od(integral, prev_err):
    od = read_od()
    error = ref_od - od
    integral += error * wait_seconds
    pterm = kp * error
    iterm = ki * integral
    dterm = kd * (error - prev_err) / wait_seconds
    control_signal = pterm + dterm + iterm
    return integral, error, control_signal, od
