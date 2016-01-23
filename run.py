from savings_rate import SRConfig, SavingsRate, Plot

# Instantiate a savings rate config object
config = SRConfig('ini', 'config/config.ini')

# Instantiate a savings rate object for a user
savings_rate = SavingsRate(config)
monthly_rates = savings_rate.get_monthly_savings_rates()

# Plot the user's savings rate
user_plot = Plot(savings_rate)
user_plot.plot_savings_rates(monthly_rates)

