The FetchData module must contain two elements:

1. A function to fetch the option chain of a given stock from the Invertir Online API. It will have one parameter: the stock symbol.

It will store the data in a csv file in the data folder. The file will be named as: <stock_symbol>_option_chain_<date>.csv

The table structure will be as follows:
symbol,last_price,date

The file "response_example.json" contains an example of the response from the API. Use it to test the function, and also to create the csv file.

<!-- 2. It will have a user interface to input the stock symbol. The user interface will be similar to the one in the Login module.

Even if the token is already in the token.txt file, it must always perform the login process in the FetchData module. 

Notice that the token must come from the user interface of the Login module. -->