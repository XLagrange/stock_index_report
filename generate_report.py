import io
import csv
import datetime
import smtplib
import yahoo_finance
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders


DATA_PATH = './data/'
OUTPUT_PATH = './output/'

INDEXES = [
	'^IXIC',  # nasdaq
	'^DJI',  # Dow 30
	'^GSPC',  # S&P 500
	'^GSPTSE',  # S&P/TSX Composite index
]

INDEX_TO_NAME = {
	'^IXIC': 'NASDAQ',
	'^DJI': 'DOW',
	'^GSPC': 'S&P 500',
	'^GSPTSE': 'S&P/TSX Composite index',
}

TIME_RANGES = [
	None, 
	relativedelta(years=-5),
	relativedelta(years=-1),
	relativedelta(months=-6),
	relativedelta(months=-3),
]

TIME_RANGES_TITLES = [
	'MAX',
	'5 YEARS',
	'12 MONTHS',
	'6 MONTHS',
	'3 MONTHS',
]

CSV_FIELDS = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']

EMAIL_FROM = 'xili.raspberrypi@gmail.com'
EMAIL_RECEIPIENTS = 'xi.lagrange@gmail.com, dsy612@gmail.com'


def send_email(index_buf_map):
	msg = MIMEMultipart()
	msg['Subject'] = 'Stock Market Index Report for %s' % datetime.date.today().isoformat()
	msg['From'] = EMAIL_FROM
	msg['To'] = EMAIL_RECEIPIENTS

	body = "Daily Report"
	msg.attach(MIMEText(body, 'plain'))

	for index, buf in index_buf_map.items():
		part = MIMEBase('application', "octet-stream")
		part.set_payload(buf.read())
		encoders.encode_base64(part)
		part.add_header('Content-Disposition', 'attachment; filename="%s.png"' % index)
		msg.attach(part)

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.login(EMAIL_FROM, "wangzhen")
	text = msg.as_string()
	server.sendmail(EMAIL_FROM, EMAIL_RECEIPIENTS, text)
	server.quit()


def plot_chart(plot_stats, index):
	buf = io.BytesIO()
	plt.figure(figsize=(20, 20))
	plt.suptitle('Index Time Series of %s' % INDEX_TO_NAME[index])
	start_index = 1
	for x, y in plot_stats:
		plt.subplot(510 + start_index)
		plt.plot(x, y, 'r--', linewidth=1)
		plt.title(TIME_RANGES_TITLES[start_index - 1])
		plt.grid(True)
		start_index += 1
	plt.subplots_adjust(top=0.95, bottom=0.05, left=0.05, right=0.95, hspace=0.25, wspace=0.35)
	plt.savefig(buf)
	buf.seek(0)
	return buf


def get_data_since_time(time, data):
	x = []
	y = []
	for key in sorted(data.keys()):
		if key == 'null' or data[key] == 'null':
			continue

		if time is not None and key < time:
			continue

		x.append(datetime.datetime.strptime(key, '%Y-%m-%d'))
		y.append(float(data[key]))

	return x, y


if __name__ == '__main__':

	today = datetime.date.today()

	nasdaq = yahoo_finance.Share('^IXIC')
	trade_date = datetime.datetime.strptime(nasdaq.get_trade_datetime()[0:10], '%Y-%m-%d').date()

	if today > trade_date:
		# today is not a trade day
		return

	# populate the csv
	for index in INDEXES:
		filename = DATA_PATH + index + '.csv'

		data_dict = {}
		with open(filename, 'a') as csvfile:
			writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
			share = yahoo_finance.Share(index)
			writer.writerow(
				{
					'Date': trade_date,
					'Close': share.get_price()
				}
			)

	index_buf_map = {}

	for index in INDEXES:
		filename = DATA_PATH + index + '.csv'

		data_dict = {}

		with open(filename) as csvfile:
			reader = csv.DictReader(csvfile)
			for row in reader:
				data_dict[row['Date']] = row['Close']
			plot_stats = []
			for time_range in TIME_RANGES:
				if time_range:
					since_time = today + time_range 
					since_time = since_time.isoformat()
				else:
					since_time = None
				plot_stats.append(get_data_since_time(since_time, data_dict))
			index_buf_map[index] = plot_chart(plot_stats, index)

	send_email(index_buf_map)


