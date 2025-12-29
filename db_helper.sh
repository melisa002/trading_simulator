#!/bin/bash
# Safe database helper script
# Use this instead of manually editing the database file!

cd "$(dirname "$0")/infolder"

echo "🗃️  Database Helper"
echo "=================="
echo ""
echo "Choose an option:"
echo "1. View all users"
echo "2. View user's cash balance"
echo "3. Update user's cash (SAFE)"
echo "4. View user's transactions"
echo "5. View database schema"
echo "6. Run custom SQL query"
echo "7. Database integrity check"
echo "8. Exit"
echo ""
read -p "Enter option (1-8): " option

case $option in
    1)
        echo ""
        echo "All Users:"
        sqlite3 finance.db "SELECT id, username, cash FROM users;"
        ;;
    2)
        read -p "Enter username: " username
        sqlite3 finance.db "SELECT username, cash FROM users WHERE username = '$username';"
        ;;
    3)
        read -p "Enter username: " username
        read -p "Enter new cash amount: " cash
        sqlite3 finance.db "UPDATE users SET cash = $cash WHERE username = '$username';"
        echo "✅ Cash updated for $username"
        sqlite3 finance.db "SELECT username, cash FROM users WHERE username = '$username';"
        ;;
    4)
        read -p "Enter username: " username
        echo ""
        sqlite3 finance.db << EOF
SELECT t.timestamp, t.symbol, t.shares, t.price, (t.shares * t.price) as total
FROM transactions t
JOIN users u ON t.user_id = u.id
WHERE u.username = '$username'
ORDER BY t.timestamp DESC;
EOF
        ;;
    5)
        sqlite3 finance.db ".schema"
        ;;
    6)
        read -p "Enter SQL query: " query
        sqlite3 finance.db "$query"
        ;;
    7)
        result=$(sqlite3 finance.db "PRAGMA integrity_check;")
        if [ "$result" = "ok" ]; then
            echo "✅ Database is healthy!"
        else
            echo "❌ Database has issues: $result"
        fi
        ;;
    8)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid option"
        ;;
esac

