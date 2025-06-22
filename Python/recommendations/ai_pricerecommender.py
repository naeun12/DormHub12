from flask import Flask, request, jsonify
import pymysql
import pandas as pd

app = Flask(__name__)

def get_recommendations(min_price, max_price, top_n=10):
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='capstonedormhub',
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:
            query = """
            SELECT d.dorm_name, d.address, d.latitude, d.longitude, r.price
            FROM rooms r
            JOIN dorms d ON r.dormitory_id = d.dorm_id
            WHERE r.price IS NOT NULL AND LOWER(r.availability) = 'available';
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            print(f"Fetched rows: {rows}")

    finally:
        connection.close()

    # Now convert rows list of dicts into a DataFrame
    df = pd.DataFrame(rows)
    print("DF head:\n", df.head())

    # Convert price column to numeric
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    print("Prices after conversion:", df['price'].tolist())

    # Filter by price range
    filtered = df[(df['price'] >= min_price * 0.8) & (df['price'] <= max_price * 1.2)]
    print("Filtered rows count:", len(filtered))

    recommended = filtered.sort_values(by='price').head(top_n)
    print("Recommended rows count:", len(recommended))

    return recommended[['dorm_name', 'address', 'price']].to_dict(orient='records')


@app.route('/api/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        min_price = float(data.get('min_price', 0)) if data.get('min_price') is not None else 0
        max_price = float(data.get('max_price', 999999)) if data.get('max_price') is not None else 999999

        recommendations = get_recommendations(min_price, max_price)
        print("min_price type:", type(min_price))
        print("max_price type:", type(max_price))
        
        return jsonify({'status': 'success', 'data': recommendations})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    

if __name__ == '__main__':
    app.run(debug=True)
