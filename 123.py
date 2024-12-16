class Legislative:
    def __init__(self, date, number):
        self.bills = []
        print("Legislative Yuan is established")
        print("Date: ", date)
        print("Number: ", number)

    def add_bill(self, bill, way):
        # Add a new bill with its discussion method
        self.bills.append((int(bill), way))

    def Bills(self):
        # Sort bills by bill number
        self.bills.sort(key=lambda x: x[0])
        print("\nArrange by bills")
        self.showing_meeting()

    def Ways(self):
        self.bills.sort(key=lambda x: (x[1], x[0]))
        print("\nArrange by ways")
        self.showing_meeting()

    def showing_meeting(self):
        print("Today's meeting")
        for bill, way in self.bills:
            print(f"{bill} {way}")

# Main program logic
if __name__ == "__main__":
    line = input()
    date, number = line.split()
    legislative = Legislative(date, number)
    while True:
        line = input()
        if line == "q":
            break
        bill, way = line.split()
        legislative.add_bill(bill, way)

    # Call the methods in the required order
    legislative.showing_meeting()
    legislative.Bills()
    legislative.Ways()