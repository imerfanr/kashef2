Module HelloWorld
    Sub Main()
        ' نمایش پیام خوش‌آمدگویی
        System.Console.WriteLine("Hello VB!")
        System.Console.WriteLine("لطفاً نام خود را وارد کنید:")
        Dim userName As String = System.Console.ReadLine()

        If String.IsNullOrEmpty(userName) Then
            System.Console.WriteLine("نامی وارد نشده، خوش‌آمد به کاربر ناشناس!")
        Else
            System.Console.WriteLine("سلام، " & userName & "! به این برنامه ویژوال بیسیک خوش آمدید!")
        End If

        ' بررسی زوج یا فرد بودن عدد
        System.Console.WriteLine("لطفاً یک عدد برای بررسی زوج یا فرد بودن وارد کنید:")
        Dim input As String = System.Console.ReadLine()
        Dim number As Integer

        If Integer.TryParse(input, number) Then
            If number Mod 2 = 0 Then
                System.Console.WriteLine("عدد " & number & " زوج است!")
            Else
                System.Console.WriteLine("عدد " & number & " فرد است!")
            End If
        Else
            System.Console.WriteLine("ورودی نامعتبر! لطفاً یک عدد معتبر وارد کنید.")
        End If

        ' دریافت اطلاعات IP از کاربر
        System.Console.WriteLine("لطفاً یک آدرس IP برای بررسی وارد کنید (مثال: 192.168.1.1):")
        Dim ipAddress As String = System.Console.ReadLine()

        ' دریافت اطلاعات شبکه‌ای از ip-api.com
        Dim networkInfo As String = ""
        Try
            Dim client As New System.Net.WebClient()
            networkInfo = client.DownloadString("http://ip-api.com/json/" & ipAddress & "?fields=status,country,city,lat,lon,isp,org")
            System.Console.WriteLine("اطلاعات شبکه دریافت شد: " & networkInfo)
        Catch ex As Exception
            System.Console.WriteLine("خطا در دریافت اطلاعات شبکه: " & ex.Message)
            networkInfo = "{""status"": ""fail"", ""message"": """ & ex.Message & """}"
        End Try

        ' دریافت لاگ‌های اسکن از سرور Suricata (در صورت وجود)
        Dim suricataLogs As String = ""
        Try
            Dim client As New System.Net.WebClient()
            suricataLogs = client.DownloadString("http://localhost:5000/logs")
            System.Console.WriteLine("لاگ‌های اسکن Suricata دریافت شد.")
        Catch ex As Exception
            System.Console.WriteLine("خطا در دریافت لاگ‌های Suricata: " & ex.Message)
            suricataLogs = "[]"
        End Try

        ' ذخیره داده‌ها به‌صورت JSON
        Try
            Dim filePath As String = "user_data.json"
            Dim dataToSave As String = "{" & _
                """timestamp"": """ & DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") & """," & _
                """userName"": """ & userName.Replace("""", "\""") & """," & _
                """number"": """ & input & """," & _
                """ipAddress"": """ & ipAddress & """," & _
                """networkInfo"": " & networkInfo & "," & _
                """suricataLogs"": " & suricataLogs & _
                "}"
            System.IO.File.AppendAllText(filePath, dataToSave & Environment.NewLine)
            System.Console.WriteLine("داده‌ها با موفقیت در فایل " & filePath & " ذخیره شدند.")
        Catch ex As Exception
            System.Console.WriteLine("خطا در ذخیره داده‌ها: " & ex.Message)
        End Try

        ' انتظار برای ورودی کاربر برای خروج
        System.Console.WriteLine("برای خروج یک کلید فشار دهید...")
        System.Console.ReadKey()
    End Sub
End Module