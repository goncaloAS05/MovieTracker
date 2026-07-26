import singlestoredb as s2

# Create a connection to the database
conn = s2.connect("gonçalo-1d73d:s%7DZ9dG0Ms*X%5B2UD5SBl%2BX%5B_@svc-3482219c-a389-4079-b18b-d50662524e8a-shared-dml.aws-virginia-6.svc.singlestore.com:3333/db_gonalo_2602a")

# Check if the connection is open
with conn:
    with conn.cursor() as cur:
        flag = cur.is_connected()
        print(flag)