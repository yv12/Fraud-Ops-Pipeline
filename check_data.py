import csv

def analyze_data(filepath):
    total_rows = 0
    fraud_count = 0
    normal_count = 0
    min_time = float('inf')
    max_time = 0.0
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            
            if row['Class'] == '1':
                fraud_count += 1
            else:
                normal_count += 1
                
            time_val = float(row['Time'])
            if time_val < min_time:
                min_time = time_val
            if time_val > max_time:
                max_time = time_val
                
    fraud_percentage = (fraud_count / total_rows) * 100 if total_rows > 0 else 0
    time_span_hours = (max_time - min_time) / 3600
    
    print(f"Total rows (transactions): {total_rows}")
    print(f"Normal transactions: {normal_count}")
    print(f"Fraud transactions: {fraud_count}")
    print(f"Fraud percentage: {fraud_percentage:.4f}%")
    print(f"Time span: {time_span_hours:.2f} hours")

if __name__ == '__main__':
    analyze_data(r'd:\Fraud detection\Data\creditcard.csv')
