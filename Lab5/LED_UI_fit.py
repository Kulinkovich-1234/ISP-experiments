import argparse
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


def diode_model(U, I0, n):
    Vt = 0.026
    return I0 * (np.exp(U / (n * Vt)) - 1)


def exp_model(U, a, b):
    return a * np.exp(b * U)


def rmse(y_true, y_pred):
    return math.sqrt(np.mean((y_true - y_pred) ** 2))


def load_data(path):
    data = np.loadtxt(path, delimiter=',')
    U = data[:, 0]
    V_in = data[:, 1]
    I = V_in / 47.0
    return U, I


def fit_model_with_restarts(model, U, I, guesses, bounds):
    """
    Fit model to data with multiple initial guess restarts.

    Hint: I = I0 * (exp(U / (n * Vt)) - 1)  — Shockley diode equation
    You need to derive I0 (saturation current) and n (ideality factor).
    Vt = 0.026 V at room temperature.

    The exponential model is: I = a * exp(b * U)

    Implement scipy.optimize.curve_fit with the provided guess/bound arrays.
    """
    raise NotImplementedError(
        "Students must implement curve_fit for the LED I-V model. "
        "See docstring for the Shockley diode equation."
    )


def fit_models(U, I):
    # Students: Define your initial guess arrays and bounds, then call
    # fit_model_with_restarts() for both diode_model and exp_model.
    raise NotImplementedError(
        "Students must implement fit_models to call fit_model_with_restarts "
        "with appropriate initial guesses and bounds."
    )

    # After fitting, return (popt_diode, pcov_diode), (popt_exp, pcov_exp)
    # popt_diode = [I0, n]  — Shockley parameters
    # popt_exp   = [a, b]   — Exponential model parameters


def print_fit_summary(U, I, popt_diode, popt_exp):
    I_diode = diode_model(U, *popt_diode)
    I_exp = exp_model(U, *popt_exp)
    rmse_diode = rmse(I, I_diode)
    rmse_exp = rmse(I, I_exp)

    print('=== LED I-V Fit Results ===')
    print('\nDiode-like fit:')
    print(f'  I0 = {popt_diode[0]:.3e} A')
    print(f'  n  = {popt_diode[1]:.3f}')
    print(f'  RMSE = {rmse_diode:.3e} A')
    print('  Formula: I = I0 * (exp(U/(n*26mV)) - 1)')

    print('\nExponential fit:')
    print(f'  a = {popt_exp[0]:.3e} A')
    print(f'  b = {popt_exp[1]:.3e} V^-1')
    print(f'  RMSE = {rmse_exp:.3e} A')
    print('  Formula: I = a * exp(b * U)')

    better = 'diode' if rmse_diode < rmse_exp else 'exp'
    print(f'\n最佳拟合模型: {better} 模型')

    return rmse_diode, rmse_exp


def plot_results(U, I, popt_diode, popt_exp, output_path):
    U_plot = np.linspace(U.min(), U.max(), 300)
    I_diode = diode_model(U_plot, *popt_diode)
    I_exp = exp_model(U_plot, *popt_exp)

    plt.figure(figsize=(8, 5))
    plt.plot(U, I, 'o', label='Experimental data', markersize=6)
    plt.plot(U_plot, I_diode, '-', label='Diode-like fit', linewidth=2)
    plt.plot(U_plot, I_exp, '--', label='Exponential fit', linewidth=2)
    plt.xlabel('LED voltage U (V)')
    plt.ylabel('LED current I (A)')
    plt.title('LED u-I characteristic fit')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f'Fit image saved to: {output_path}')


def main():
    parser = argparse.ArgumentParser(description='LED u-I curve fitting script')
    parser.add_argument('--input', default='LED-UI.csv', help='Input CSV file path')
    parser.add_argument('--output', default='images/LED_UI_fit.png', help='Output image file path')
    args = parser.parse_args()

    U, I = load_data(args.input)
    (popt_diode, _), (popt_exp, _) = fit_models(U, I)
    print_fit_summary(U, I, popt_diode, popt_exp)
    plot_results(U, I, popt_diode, popt_exp, args.output)


if __name__ == '__main__':
    main()
