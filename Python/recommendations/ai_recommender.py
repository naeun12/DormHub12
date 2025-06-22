from flask import Flask, request, jsonify
import pymysql
import pandas as pd
import math
import re

app = Flask(__name__)

### Helper functions for recommendation ###

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
            SELECT d.dorm_name, d.address, d.latitude, d.longitude, r.price, r.room_type, r.furnishing_status, r.capacity
            FROM rooms r
            JOIN dorms d ON r.dormitory_id = d.dorm_id
            WHERE r.price IS NOT NULL AND LOWER(r.availability) = 'available'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            print(f"Fetched rows: {rows}")
    finally:
        connection.close()

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    filtered = df[(df['price'] >= min_price * 0.8) & (df['price'] <= max_price * 1.2)]
    recommended = filtered.sort_values(by='price').head(top_n)

    return recommended.to_dict(orient='records')

### Helper functions for location search ###

def normalize(text):
    return re.sub(r'[^a-z0-9]+', '', text.lower())

location_synonyms = {
    "lapulapu": ["lapu-lapu", "lapu lapu", "lapulapu", "lapulapu city"],
    "airport": ["airport", "opon", "mcac", "mactan"]
}

def keyword_matches_address(keyword, address):
    keyword_norm = normalize(keyword)
    address_norm = normalize(address)

    if keyword_norm in address_norm:
        return True

    for group, synonyms in location_synonyms.items():
        if keyword_norm in [normalize(s) for s in synonyms]:
            if any(normalize(syn) in address_norm for syn in synonyms):
                return True
    return False

def get_dorms_from_db():
    try:
        print("🛠 Connecting to DB...")
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="capstonedormhub",
            port=3306,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ Connected to DB. Fetching dorms...")

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    d.dorm_id,
                    d.dorm_name,
                    d.latitude AS lat,
                    d.longitude AS lon,
                    d.address,
                    d.occupancy_type,
                    i.main_image
                FROM dorms d
                LEFT JOIN dorm_images i ON i.dormitory_id = d.dorm_id
                WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL
            """)
            dorms = cursor.fetchall()

        conn.close()
        print("📦 Dorms fetched:", dorms)
        placeholder = "https://placehold.co/300x200?text=No+Image"

        for dorm in dorms:
            dorm['popularity'] = 7.5
            dorm['main_image'] = dorm['main_image'] or placeholder

        return dorms

    except Exception as e:
        print("❌ DB CONNECTION FAILED:", e)
        raise e

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def score_dorm(dorm, user_lat, user_lon):
    dorm_lat = float(dorm['lat'])
    dorm_lon = float(dorm['lon'])
    dist = haversine(user_lat, user_lon, dorm_lat, dorm_lon)
    score = (10 - dist) + dorm['popularity']
    return max(score, 0)

### API routes ###

@app.route('/api/recommend', methods=['POST'])
def recommend_price():
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
    

@app.route('/search-locations', methods=['POST'])
def search_locations():
    try:
        data = request.get_json()
        keyword = data.get('location', '').strip().lower()
        if not keyword:
            return jsonify({"error": "Missing location keyword"}), 400

        dorms = get_dorms_from_db()
        recommendations = []

        for dorm in dorms:
            if keyword_matches_address(keyword, dorm.get('address', '')):
                dorm['score'] = 10  # optional scoring
                recommendations.append(dorm)

        return jsonify({'status': 'success', 'recommendations': recommendations})

    except Exception as e:
        print("❌ LOCATION SEARCH ERROR:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/api/gender-recommend', methods=['POST'])
def recommend_by_gender():
        try:
            data = request.get_json()
            input_type = data.get('occupancy_type', '').strip().lower()

            dorms = get_dorms_from_db()
            recommendations = []

            for dorm in dorms:
                dorm_type = dorm.get('occupancy_type', '').strip().lower()
                if input_type == 'male' and dorm_type == 'male only':
                     recommendations.append(dorm)
                elif input_type == 'female' and dorm_type == 'female only':
                    recommendations.append(dorm)
                elif input_type == 'mixed' and 'mixed' in dorm_type:
                    recommendations.append(dorm)
                elif input_type == 'all':
                    recommendations.append(dorm)
            return jsonify({'status': 'success', 'recommendations': recommendations})

        except Exception as e:
            print("❌ GENDER RECOMMENDATION ERROR:", e)
            return jsonify({'status': 'error', 'message': str(e)}), 500    
   


if __name__ == '__main__':
    app.run(debug=True)
