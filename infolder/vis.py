


# start and end dates
start =today.strftime("%Y/%m/%d")
end = (date.today()-timedelta(days=360)).strftime("%Y/%m/%d")
symbol =
df = yf.download(symbol,start,end)
print(df)
# function to update the data
def my_function():
    df.popleft()
    df.append(price)
    ax.plot(df)
# start collections with zeros
df = collections.deque(np.zeros(10))
# define and adjust figure
fig = plt.figure(figsize=(12,6), facecolor='#DEDEDE')
ax = plt.subplot(121)
ax.set_facecolor('#DEDEDE')

# test
my_function()
plt.show()

