#!/bin/bash

echo "🚀 Starting Trading Simulator..."
echo ""
echo "📊 The app will be available at:"
echo "   👉 http://127.0.0.1:5001"
echo ""
echo "📝 Note: You need to manually open the URL in your browser"
echo "⏹️  Press CTRL+C to stop the server"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the Flask app
uv run python infolder/app.py
