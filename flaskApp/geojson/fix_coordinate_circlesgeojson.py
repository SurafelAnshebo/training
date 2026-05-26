import json

# Correct the file path using one of the methods mentioned above
with open(r'C:\Users\Surafel\Desktop\UNICEF\bvlos_flask_test\Circles.geojson', 'r') as f:
    data = json.load(f)

def swap_coordinates(coordinates):
    return [coord[::-1] for coord in coordinates]

for feature in data['features']:
    if feature['geometry']['type'] == 'Polygon':
        feature['geometry']['coordinates'] = [swap_coordinates(ring) for ring in feature['geometry']['coordinates']]

with open(r'C:\Users\Surafel\Desktop\UNICEF\bvlos_flask_test\Corrected_Circles.geojson', 'w') as f:
    json.dump(data, f, indent=2)

print("Coordinates have been swapped and saved to 'Corrected_Circles.geojson'")
