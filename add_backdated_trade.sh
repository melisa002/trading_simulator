#!/bin/bash
# Safely add backdated transactions for testing

cd "$(dirname "$0")/infolder"

echo "🔙 Add Backdated Transaction"
echo "============================="
echo ""
echo "First, let's see your user info:"
sqlite3 finance.db "SELECT id, username, cash FROM users;"
echo ""

read -p "Enter your user ID: " user_id
read -p "Enter stock symbol (e.g., AAPL): " symbol
read -p "Enter number of shares: " shares
read -p "Enter price per share: " price
read -p "Enter days ago (e.g., 7 for 7 days ago): " days_ago

# Calculate the total cost
total_cost=$(echo "$shares * $price" | bc)

# Get current cash
current_cash=$(sqlite3 finance.db "SELECT cash FROM users WHERE id = $user_id;")
new_cash=$(echo "$current_cash - $total_cost" | bc)

echo ""
echo "Transaction Summary:"
echo "  Stock: $symbol"
echo "  Shares: $shares"
echo "  Price: \$$price"
echo "  Total Cost: \$$total_cost"
echo "  Your Cash: \$$current_cash → \$$new_cash"
echo "  Date: $days_ago days ago"
echo ""

read -p "Confirm? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    # Insert the backdated transaction
    sqlite3 finance.db << EOF
INSERT INTO transactions (user_id, symbol, shares, price, timestamp)
VALUES ($user_id, '$symbol', $shares, $price, datetime('now', '-$days_ago days'));

UPDATE users SET cash = $new_cash WHERE id = $user_id;
EOF

    echo ""
    echo "✅ Transaction added successfully!"
    echo ""
    echo "Recent transactions:"
    sqlite3 finance.db << EOF
SELECT timestamp, symbol, shares, price, (shares * price) as total
FROM transactions
WHERE user_id = $user_id
ORDER BY timestamp DESC
LIMIT 5;
EOF
else
    echo "❌ Transaction cancelled"
fi
