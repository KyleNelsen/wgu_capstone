from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
from datetime import datetime
import time
import numpy as np
import traceback

# Create Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--disable-notifications")

# Initialize the Chrome driver with options
driver = webdriver.Chrome(options=chrome_options)

# Set the maximum time to wait for an element (in seconds)
wait = WebDriverWait(driver, 20)

def main():
	# variables to change
	num_stocks = 1000 # number of stocks you want to scrape, starting from the highest market cap
	
	file_path = "account.txt" # file path for stockanalyst account data in account.txt
	
	treasury_ten_year_yields = {"2024": .0406, "2023": .0396, "2022": .0295, 
	"2021": .0145, "2020": .0089, "2019": .0214, "2018": .0291, "2017": .0233, 
	"2016": .0184, "2015": .0214, "2014": .0254, "2013": .0235, "2012": .0180, 
	"2011": .0278, "2010": .0322, "2009": .0326, "2008": .0366, "2007": .0463,
	"2006": .0480, "2005": .0429, "2004": .0427, "2003": .0401, "2002": .0461,
	"2001": .0502, "2000": .0603} # used for the NPV DCF analysis, will only get data from the lowest year - npv_years
	
	data_output_file = "data.csv"

	npv_years = 10 # number of years to use when calculating npv, ex: use 2010-2020 data to predict 2021. 10 default, 5-15 recommended.
				   # Stockanalyst website only provides 10 full years of data without subscription, so have to use 9 or less to get usuable data
	
	login = True  # optional to login, able to get more years of data with subscription. Careful not to spam too much or you will get a captcha. True / False

	# functions to run
	scrape_main(num_stocks, treasury_ten_year_yields, data_output_file, npv_years, login, file_path)
	

def scrape_main(num_stocks, treasury_ten_year_yields, data_output_file, npv_years, login, file_path):
	"""
    Gathers all data and returns a pandas dataframe
    Inputs: 
    num_stocks - number of stocks to get data of
	treasury_ten_year_yields - 10 year us treasury yields
	data_output_file - file all of the data is saved to
    """
    
	# some of the html numbers change when you login, so "l" will take care of it
	if login == True:
		login_website(file_path)

	# creating a pandas dataframe
	my_columns = ["ticker", "year", "marketcap", "eps", "earnings_rate", "price", "price_rate", "pe_ratio", "roe", "sh_equity", "sh_return", "real_change"]
	df = pd.DataFrame(columns=my_columns)

	# loops through the stocks in the list and adds them to the dataframe til it reaches the limit
	i = 1
	while i < num_stocks+1:
		# goes to list of stocks ordered by market cap
		driver.get('https://stockanalysis.com/list/biggest-companies/')

		# expands list to 1000
		button = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main"]/div/div/div/nav/div/div/button')))
		button.click()
		tho_rows = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main"]/div/div/div/nav/div/div/div/button[3]')))
		tho_rows.click()

		# Wait for the element to be present visible
		ticker_element = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main-table"]/tbody/tr['+str(i)+']/td[2]/a')))
		ticker = ticker_element.text
		print(i, ticker)

		row_link = ticker_element.get_attribute('href')
		try:
			row_data = scrape_stock(row_link, ticker, my_columns, treasury_ten_year_yields, npv_years)
			# row_data is false if the stock has less than 12 years(11 full years) of data.
			if row_data != False:
				new_data = pd.DataFrame(row_data, columns=my_columns)
				df = pd.concat([df, new_data], ignore_index=True)
			# save data to file
			df.to_csv(data_output_file, index=False)
			i = i + 1
		except:
			i = i + 1
			pass

	# closes driver
	driver.close()

def scrape_stock(row_link, ticker, my_columns, treasury_ten_year_yields, npv_years):
	"""
    Scrapes all the required data for an individual company and returns a number of rows worth of data. 
    Returns False if stock has less than 12 years(11 full years) of data.
    Inputs: 
    row_link - url of stock
	ticker - ticker name of stock
	my_columns - pandas df columns
	treasury_ten_year_yields - 10 year us treasury yields
    """

	try:
	    # driver goes to stock page
		driver.get(row_link)

		price_current = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main"]/div[1]/div[2]/div[1]/div[1]')))

	    # clicks on Financials tab
		driver.find_element(By.XPATH,'//*[@id="main"]/div[1]/nav/ul/li[2]/a').click()
		wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main"]/div[3]/div[2]/button[2]')))

		# clicks on ttm button to include most recent data
		ttm_button = driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/div[2]/button[2]').click()
		
		# gets count of how many years in the table, gets table with least years
		try:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/thead/tr')
		except:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/thead/tr')
		n = header.find_elements(By.CLASS_NAME, 'border-b')
		n_years_i = len(n)

		# clicks on Ratios tab
		driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[4]/a').click()
		time.sleep(1)

		# gets count of how many years in the table, gets table with least years
		try:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/thead/tr')
		except:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/thead/tr')
		n = header.find_elements(By.CLASS_NAME, 'border-b')
		n_years_r = len(n)

		# clicks on Cashflow tab
		driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[3]/a').click()
		time.sleep(1)

		# gets count of how many years in the table, gets table with least years
		try:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/thead/tr')
		except:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/thead/tr')
		n = header.find_elements(By.CLASS_NAME, 'border-b')
		n_years_c = len(n)

		# clicks on Balance Sheet tab
		driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[2]/a').click()
		time.sleep(1)

		# gets count of how many years in the table, gets table with least years
		try:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/thead/tr')
		except:
			header = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/thead/tr')
		n = header.find_elements(By.CLASS_NAME, 'border-b')
		n_years_b = len(n)

		# figures out which table has the least amount of years of data, and uses that amount of years
		n_years = n_years_i
		if n_years_c < n_years:
			n_years = n_years_c
		elif n_years_r < n_years:
			n_years = n_years_r
		elif n_years_b < n_years:
			n_years = n_years_b

		# clicks on Income tab
		driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[1]/a').click()
		time.sleep(1)

		# continues if stock has enough data, else returns and moves on to next stock
		if n_years > npv_years:

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "Shares Outstanding (Basic)":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all shares outstanding (basic)
				shares = []
				j = 0
				while j < n_years-1:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					if d != "Upgrade":
						shares.append(d.replace(",", ""))
						j = j + 1
					else:
						break
			else:
				print("Shares False")
				return False

			n = j

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "EPS (Basic)":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all EPS (Basic)
				eps = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					if d != "Upgrade":
						eps.append(d.replace(",", ""))
						j = j + 1
					else:
						break
			else:
				print("EPS False")
				return False

			# loops through table and collects all years
			years = []
			j = 0
			while j < n:
				try:
					d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/thead/tr/th[' +str(j+2)+ ']').text
				except:
					d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/thead/tr/th[' +str(j+2)+ ']').text
				if d == "TTM" or d == "Current":
					d = str(datetime.now().year)
				years.append(d)
				j = j + 1

		    # clicks on Ratios tab
			driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[4]/a').click()
			time.sleep(1)

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "Market Capitalization":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all market capitalizations
				mcs = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					mcs.append(d.replace(",", ""))
					j = j + 1
			else:
				print("MC False")
				return False

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "PE Ratio":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all PE Ratio
				pe_ratios = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					pe_ratios.append(d.replace(",", ""))
					j = j + 1
			else:
				print("PE Ratio False")
				return False

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "Return on Equity (ROE)":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all Return on Equity (ROE)
				roe = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					roe.append(d.replace("%", ""))
					j = j + 1
			else:
				print("ROE False")
				return False

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "Total Shareholder Return":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all Total Shareholder Return
				tsh = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					tsh.append(d.replace("%", ""))
					j = j + 1
			else:
				print("TSH False")
				return False

			# clicks on Cashflow tab
			driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[3]/a').click()
			time.sleep(1)

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "Net Income":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all PE Ratio
				earnings = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					earnings.append(d.replace(",", ""))
					j = j + 1
			else:
				print("Net Income False")
				return False

			# clicks on Balance Sheet tab
			driver.find_element(By.XPATH,'//*[@id="main"]/div[2]/nav[1]/ul/li[2]/a').click()
			time.sleep(1)

			# finds row number with appropiate name
			try:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody')
			except:
				tbody = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody')
			num_rows = tbody.find_elements(By.CSS_SELECTOR, 'tr')
			j = 0
			found = False
			for _ in num_rows:
				row_name = num_rows[j].find_elements(By.CSS_SELECTOR, 'td')
				if row_name[0].text == "Shareholders' Equity":
					r = j + 1
					found = True
				j = j + 1

			if found == True:
				# loops through table and collects all Shareholders' Equity
				she = []
				j = 0
				while j < n:
					try:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[4]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					except:
						d = driver.find_element(By.XPATH, '//*[@id="main"]/div[5]/table/tbody/tr[' +str(r)+ ']/td[' +str(j+2)+ ']').text
					she.append(d.replace(",", ""))
					j = j + 1
			else:
				print("SHE False")
				return False

			# remove all non existent data
			# Combine all arrays into a list for easy iteration
			all_arrays = [shares, eps, years, mcs, pe_ratios, roe, tsh, she, earnings]

			# Iterate over each array and find the index of "-"
			for i, array in enumerate(all_arrays):
			    try:
			        index_of_dash = array.index('-')
			        all_arrays[i] = array[:index_of_dash]  # Exclude the element with "-"
			    except ValueError:
			        pass  # "-" not found in the array

			# Separate the updated arrays
			shares, eps, years, mcs, pe_ratios, roe, tsh, she, earnings = all_arrays

			# determines years range
			# Find the minimum length among the arrays
			min_length = min(len(shares), len(eps), len(years), len(mcs), len(pe_ratios), len(roe), len(tsh), len(she), len(earnings))

			# Trim each array to the minimum length
			shares = shares[:min_length]
			eps = eps[:min_length]
			years = years[:min_length]
			mcs = mcs[:min_length]
			pe_ratios = pe_ratios[:min_length]
			roe = roe[:min_length]
			tsh = tsh[:min_length]
			she = she[:min_length]
			earnings = earnings[:min_length]

			# Convert the entire array to float using map
			shares = list(map(float, shares))
			eps = list(map(float, eps))
			mcs = list(map(int, mcs))
			pe_ratios = list(map(float, pe_ratios))
			roe = list(map(float, roe))
			tsh = list(map(float, tsh))
			she = list(map(float, she))
			earnings = list(map(float, earnings))

			# loops through and calculates prices
			prices = []
			j = 0
			while j < len(mcs):
				p = (mcs[j] / shares[j])
				prices.append(p)
				j = j + 1

			# loops through years to create 11 year period rows
			new_rows = []
			j = 0
			while j < len(years)-npv_years:
				year = years[j]
				last_year = list(treasury_ten_year_yields.keys())[-1]
				# can only get data from year with a provided treasury yield
				if datetime.strptime(year, '%Y') > datetime.strptime(last_year, '%Y'):
					marketcap = mcs[j]
					share = shares[j]
					p_current = prices[j]
					current_price = round(p_current,2)
					price_rate = round(average_growth_rate(prices[j:j+npv_years]),4)
					current_sh_equity = int(she[j])
					current_eps = eps[j]
					earnings_rate = round(average_growth_rate(earnings[j:j+npv_years]),4)
					current_pe_ratio = pe_ratios[j]
					current_roe = roe[j]
					current_tsh = tsh[j]
					# don't know the future year prices yet
					if years.index(year) != 0:
						p_current = prices[j]
						p_after = prices[j-1]
						real_change = round(((p_after - p_current) / p_current)*100,2)
					else: 
						real_change = None

					new_row = [ticker, year, marketcap, current_eps, earnings_rate, current_price, price_rate, current_pe_ratio, current_roe, current_sh_equity, current_tsh, real_change]
					new_rows.append(new_row)
					j = j + 1
				else:
					break

			return new_rows
		else:
			print("has less years than needed,", n_years)
			return False
	except Exception:
		traceback.print_exc()
		return False

def login_website(file_path):
	"""
    Logs in to stockanalysis
    Inputs: 
    file_path - filepath to accounts.txt
    """

	driver.get('https://stockanalysis.com/login/')

	# Open the file in read mode ('r')
	with open(file_path, 'r') as file:
	    # Read the lines from the file
	    lines = file.readlines()

	# Extract email and password from the lines
	for line in lines:
	    if line.startswith('Email ='):
	        email = line.split('=')[1].strip().replace('"','')
	    elif line.startswith('Password ='):
	        password = line.split('=')[1].strip().replace('"','')

	wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="email"]')))
	email_field = driver.find_element(By.XPATH,'//*[@id="email"]').send_keys(email)
	password_field = driver.find_element(By.XPATH,'//*[@id="password"]').send_keys(password)
	login_button = driver.find_element(By.XPATH,'//*[@id="main"]/div/form/button').click()

def npv_per_share(ocf, discount_rate, shares, p_current, rate):
	"""
	Calculates npv per share and returns it. Doesn't subtract initial investment so this is what the price should be at the time.
	Inputs: 
	ocf - last 10 years of operating cash flows
	discount_rate - discount rate, using 10yr treasury yield
	shares - number of shares
	rate - ocf growth rate
	"""

	# Predicting future cash flow with growth rate
	future_cfs = []
	j = 0
	c = ocf[0]
	while j < len(ocf):
		c = c + (c * rate)
		future_cfs.append(c)
		j = j + 1

	npv = sum([cf / (1 + discount_rate) ** t for t, cf in enumerate(future_cfs)])
	npv = npv / shares
	npv = npv - p_current

	return round(npv,2)

def average_growth_rate(array):
	"""
    Calculates average growth rate of the array and returns it
    Inputs: 
    array - array of values
    """
	growth_rates = []
	j = 0
	while j < len(array) - 1:
		r = ((array[-2-j] - array[-1-j]) / array[-1-j])
		growth_rates.append(r)
		j = j + 1
	average_rate = sum(growth_rates) / len(growth_rates)

	return average_rate


# Run main when the script is executed
if __name__ == "__main__":
    main()