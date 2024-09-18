import pandas as pd
from decimal import Decimal, getcontext
from calendar import monthrange

# Set decimal precision
getcontext().prec = 10

def get_dates_debt():
    """
    Prompt the user to input the start and end dates and the initial debt amount.
    Returns:
        start_date (Timestamp): Start date in YYYY-MM-DD format.
        end_date (Timestamp): End date in YYYY-MM-DD format.
        initial_debt (Decimal): Initial debt amount in MXN.
    """

    start_date = pd.to_datetime(input("• Introduce la fecha de exigibilidad legal (inicio) [YYYY-MM-DD]: "))
    end_date = pd.to_datetime(input("• Introduce la fecha de resolución (fin) [YYYY-MM-DD]: "))
    initial_debt = Decimal(input("• Introduce la suerte principal en MXN: "))
    return start_date, end_date, initial_debt

def get_udi_mxn(date):
    """
    Fetch the UDI-MXN exchange rate for a given date from a CSV file.
    Args:
        date (Timestamp): Date for which to retrieve the UDI-MXN rate.
    Returns:
        Decimal: UDI-MXN rate for the given date or None if not found.
    """

    udi_mxn_rates_file = "udi-mxn-20240918.csv"
    df = pd.read_csv(
        udi_mxn_rates_file, skiprows=19, names=["Date", "Value"],
        parse_dates=["Date"], date_format="%d/%m/%Y", encoding="windows-1252"
    )
    result = df[df['Date'] == date]
    return Decimal(result['Value'].values[0]) if not result.empty else None

def get_default_compensation(start_date, end_date, initial_debt):
    """
    Calculate the default compensation based on UDI rates.
    Args:
        start_date (Timestamp): Start date of the debt.
        end_date (Timestamp): End date of the debt.
        initial_debt (Decimal): Initial debt amount in MXN.
    Returns:
        Decimal: Default compensation amount or None if rates are not available.
    """

    start_udi_mxn_rate = get_udi_mxn(start_date)
    end_udi_mxn_rate = get_udi_mxn(end_date)

    if start_udi_mxn_rate is None or end_udi_mxn_rate is None:
        print("Alguna de las dos fechas no está en el dataset. Quoi faire ?")
        return None

    # Calculate adjusted initial debt based on UDI rates
    adjusted_initial_debt = initial_debt * (end_udi_mxn_rate / start_udi_mxn_rate)
    return adjusted_initial_debt - initial_debt

def get_month_days(start_date, end_date):
    """
    Get the number of days in each month between the start and end dates.
    Args:
        start_date (Timestamp): Start date.
        end_date (Timestamp): End date.
    Returns:
        List[dict]: List of dictionaries with year, month, and days in that month.
    """

    month_days = []
    current_date = start_date

    while current_date <= end_date:
        total_days_in_month = monthrange(current_date.year, current_date.month)[1]

        # Calculate days in the start month
        if current_date.month == start_date.month and current_date.year == start_date.year:
            days_in_month = total_days_in_month - current_date.day + 1
        else:
            days_in_month = total_days_in_month

        # Adjust for end date
        if current_date.month == end_date.month and current_date.year == end_date.year:
            days_in_month = end_date.day

        month_days.append({
            "year": current_date.year,
            "month": current_date.month,
            "days_in_month": days_in_month
        })

        # Move to the next month
        current_date = (current_date + pd.DateOffset(months=1)).replace(day=1)

    return month_days

def get_default_interest(start_date, end_date, initial_debt):
    """
    Calculate default interest based on the CCP-UDI rate and the days within each month.
    Args:
        start_date (Timestamp): Start date.
        end_date (Timestamp): End date.
        initial_debt (Decimal): Initial debt in MXN.
    """

    ccp_udi_rates_file = "ccp-udi-20240918.csv"
    df = pd.read_csv(
        ccp_udi_rates_file, skiprows=19,
        names=["Date", "CCP-MXN", "CCPO-MXN", "CCP-UDI", "CCP-USD", "CPP", "CCPE", "TIPP"],
        parse_dates=["Date"], date_format="%d/%m/%Y", encoding="windows-1252"
    )

    # Convert initial debt to UDI
    initial_debt_udi = initial_debt / get_udi_mxn(start_date)
    df_timeframe = df[(df["Date"] >= start_date.replace(day=1)) & (df["Date"] <= end_date)]
    month_days = get_month_days(start_date, end_date)

    total_interest_udi = Decimal(0)
    for i, row in df_timeframe.iterrows():
        try:
            current_ccp_udi = Decimal(row["CCP-UDI"])
            current_daily_default_rate = current_ccp_udi * Decimal(1.25) / Decimal(365)

            # Calculate monthly default rate
            row_date = row["Date"]
            for month in month_days:
                if row_date.year == month["year"] and row_date.month == month["month"]:
                    current_monthly_default_rate = current_daily_default_rate * Decimal(month["days_in_month"]) / Decimal(100)
                    total_interest_udi += initial_debt_udi * current_monthly_default_rate
                    break
        except ValueError:
            print(f"No hay valor CCP-UDI para la fecha {row['Date'].strftime('%Y-%m-%d')}")

    return total_interest_udi * get_udi_mxn(end_date)

def main():
    """
    Main function to get user inputs, calculate compensation and interest, and display results.
    """
    start_date, end_date, initial_debt = get_dates_debt()
    default_compensation = get_default_compensation(start_date, end_date, initial_debt)

    if default_compensation is not None:
        print(f"\n-> La indemnización por mora es de: ${default_compensation:,.2f}")

    default_interest = get_default_interest(start_date, end_date, initial_debt)
    print(f"-> El interés por mora: ${default_interest:,.2f}")

    print(f"\n---> El total que se debe pagar es de ${initial_debt + default_compensation + default_interest:,.2f}")

if __name__ == "__main__":
    main()
