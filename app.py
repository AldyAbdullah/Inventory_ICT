from flask import Flask, render_template

app = Flask(__name__)

# Data inventaris sementara (nanti kita ganti dengan database)
inventaris = [
    {"id": 1, "nama_barang": "Laptop ThinkPad", "jumlah": 10},
    {"id": 2, "nama_barang": "Mouse Wireless", "jumlah": 25},
]

@app.route('/')
def index():
    return render_template('index.html', data=inventaris)

if __name__ == '__main__':
    app.run(debug=True)