class FinancialMetricsDBEntity:
    def __init__(self, company_Name='', reporting_year=0, assets=0.00, liabilities=0.00,
                 equity=0.00, revenue=0.00, operating_expense=0.00, ebitda=0.00, net_income=0.00,
                 eps=0.00, cf_investing=0.00, cf_operations=0.00, cf_financing=0.00, free_cash_flow=0.00, stock_price=0.00, 
                 pe_ratio=0.00, roa=0.00, exchange_ref='',beta_calender_year_end=0.00,sharpe_ratio=0.00) -> None:

        self.company_Name = company_Name
        self.reporting_year = reporting_year
        self.assets = assets
        self.liabilities = liabilities
        self.equity = equity
        self.revenue = revenue
        self.operating_expense = operating_expense
        self.ebitda = ebitda
        self.net_income = net_income
        self.eps = eps
        self.cf_investing = cf_investing
        self.cf_operations = cf_operations
        self.cf_financing = cf_financing
        self.free_cash_flow = free_cash_flow
        self.stock_price = stock_price
        self.pe_ratio = pe_ratio
        self.roa = roa
        self.exchange_ref = exchange_ref
        self.beta_calender_year_end = beta_calender_year_end
        self.sharpe_ratio=sharpe_ratio