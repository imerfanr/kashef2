Imports System.Net
Imports System.Text.RegularExpressions
Imports System.IO
Imports Newtonsoft.Json
Imports Microsoft.AspNetCore.SignalR
Imports Microsoft.AspNetCore.SignalR.Client
Imports System.Windows.Forms
Imports System.Drawing
Imports Microsoft.ML
Imports Microsoft.ML.Data
Imports System.Security.Cryptography
Imports System.Text
Imports Microsoft.AspNetCore.Builder
Imports Microsoft.Extensions.DependencyInjection
Imports Microsoft.AspNetCore.Hosting
Imports System.Threading.Tasks
Imports System.Windows.Forms.DataVisualization.Charting
Imports iText.Kernel.Pdf
Imports iText.Layout
Imports iText.Layout.Element

' کلاس داده برای ML.NET
Public Class NetworkData
    <LoadColumn(0)>
    Public Property Lat As Single
    <LoadColumn(1)>
    Public Property Lon As Single
    <LoadColumn(2)>
    Public Property HasMiningPorts As Boolean
    <LoadColumn(3), ColumnName("Label")>
    Public Property IsMiner As Boolean
End Class

Public Class NetworkDataPrediction
    <ColumnName("PredictedLabel")>
    Public Property IsMiner As Boolean
End Class

' کلاس هاب SignalR
Public Class ChatHub
    Inherits Hub
    Public Async Function SendMessage(message As String) As Task
        Await Clients.All.SendAsync("ReceiveMessage", message)
    End Function
End Class

Public Class MinerDetectorForm
    Inherits Form

    Private WithEvents txtUserName As TextBox
    Private WithEvents txtNumber As TextBox
    Private WithEvents txtIPAddress As TextBox
    Private WithEvents btnSubmit As Button
    Private WithEvents btnExportCsv As Button
    Private WithEvents btnExportPdf As Button
    Private WithEvents txtOutput As TextBox
    Private WithEvents chkNmap As CheckBox
    Private WithEvents chkSuricata As CheckBox
    Private WithEvents txtChat As TextBox
    Private WithEvents btnSendChat As Button
    Private chart As Chart
    Private hubConnection As HubConnection
    Private mlContext As MLContext
    Private model As ITransformer
    Private userList As New List(Of String)
    Private Const AES_KEY As String = "b14ca5898a4e4133bbce2ea2315a1916"
    Private XAI_API_KEY As String = "YOUR_XAI_API_KEY" ' جایگزین با کلید واقعی
    Private networkSettings As New Dictionary(Of String, String) From {{"defaultIP", "192.168.1.1"}, {"ports", "3333,4444,1800,4028"}}

    Public Sub New()
        ' تنظیمات فرم
        Me.Text = "سیستم تشخیص ماینر"
        Me.Size = New Size(1000, 800)
        Me.FormBorderStyle = FormBorderStyle.FixedSingle
        Me.MaximizeBox = False

        ' منوی اصلی
        Dim mainMenu As New MenuStrip()
        Dim adminMenu As New ToolStripMenuItem("مدیریت")
        Dim scanMenu As New ToolStripMenuItem("اسکن شبکه")
        Dim analysisMenu As New ToolStripMenuItem("تحلیل")
        Dim settingsMenu As New ToolStripMenuItem("تنظیمات")

        ' زیرمنوهای مدیریت
        adminMenu.DropDownItems.Add("افزودن کاربر", Nothing, AddressOf MenuAddUser_Click)
        adminMenu.DropDownItems.Add("حذف کاربر", Nothing, AddressOf MenuRemoveUser_Click)
        adminMenu.DropDownItems.Add("نمایش لاگ‌ها", Nothing, AddressOf MenuLogs_Click)
        Dim subAdminMenu As New ToolStripMenuItem("مدیریت پیشرفته")
        subAdminMenu.DropDownItems.Add("پایگاه داده", Nothing, AddressOf MenuDatabase_Click)
        subAdminMenu.DropDownItems.Add("تولید گزارش", Nothing, AddressOf MenuReports_Click)
        adminMenu.DropDownItems.Add(subAdminMenu)

        ' زیرمنوهای اسکن شبکه
        scanMenu.DropDownItems.Add("اسکن سریع", Nothing, AddressOf MenuQuickScan_Click)
        scanMenu.DropDownItems.Add("اسکن کامل", Nothing, AddressOf MenuFullScan_Click)

        ' زیرمنوهای تحلیل
        analysisMenu.DropDownItems.Add("تحلیل بلادرنگ", Nothing, AddressOf MenuRealtimeAnalysis_Click)
        analysisMenu.DropDownItems.Add("تحلیل آفلاین", Nothing, AddressOf MenuOfflineAnalysis_Click)

        ' زیرمنوهای تنظیمات
        settingsMenu.DropDownItems.Add("تنظیمات شبکه", Nothing, AddressOf MenuNetworkSettings_Click)
        settingsMenu.DropDownItems.Add("تنظیمات API", Nothing, AddressOf MenuApiSettings_Click)

        mainMenu.Items.AddRange({adminMenu, scanMenu, analysisMenu, settingsMenu})
        Me.Controls.Add(mainMenu)

        ' کنترل‌های فرم
        txtUserName = New TextBox() With {.Location = New Point(20, 50), .Size = New Size(200, 25), .RightToLeft = RightToLeft.Yes}
        txtNumber = New TextBox() With {.Location = New Point(20, 100), .Size = New Size(200, 25), .RightToLeft = RightToLeft.Yes}
        txtIPAddress = New TextBox() With {.Location = New Point(20, 150), .Size = New Size(200, 25), .RightToLeft = RightToLeft.Yes}
        btnSubmit = New Button() With {.Text = "ارسال", .Location = New Point(20, 200), .Size = New Size(100, 30), .RightToLeft = RightToLeft.Yes}
        btnExportCsv = New Button() With {.Text = "خروجی CSV", .Location = New Point(130, 200), .Size = New Size(100, 30), .RightToLeft = RightToLeft.Yes}
        btnExportPdf = New Button() With {.Text = "خروجی PDF", .Location = New Point(240, 200), .Size = New Size(100, 30), .RightToLeft = RightToLeft.Yes}
        chkNmap = New CheckBox() With {.Text = "فعال‌سازی nmap", .Location = New Point(20, 240), .Size = New Size(150, 25), .RightToLeft = RightToLeft.Yes}
        chkSuricata = New CheckBox() With {.Text = "فعال‌سازی Suricata", .Location = New Point(20, 270), .Size = New Size(150, 25), .RightToLeft = RightToLeft.Yes}
        txtOutput = New TextBox() With {.Location = New Point(240, 50), .Size = New Size(700, 250), .Multiline = True, .ReadOnly = True, .RightToLeft = RightToLeft.Yes}
        txtChat = New TextBox() With {.Location = New Point(240, 310), .Size = New Size(700, 300), .Multiline = True, .RightToLeft = RightToLeft.Yes}
        btnSendChat = New Button() With {.Text = "ارسال پیام", .Location = New Point(240, 620), .Size = New Size(100, 30), .RightToLeft = RightToLeft.Yes}

        ' نمودار
        chart = New Chart() With {.Location = New Point(20, 310), .Size = New Size(200, 200)}
        Dim chartArea As New ChartArea("MainChart")
        chart.ChartAreas.Add(chartArea)
        Dim series As New Series("IPLocations") With {.ChartType = SeriesChartType.Point}
        chart.Series.Add(series)
        Me.Controls.Add(chart)

        Me.Controls.AddRange({txtUserName, txtNumber, txtIPAddress, btnSubmit, btnExportCsv, btnExportPdf, chkNmap, chkSuricata, txtOutput, txtChat, btnSendChat})

        ' برچسب‌ها
        Dim lblUserName As New Label() With {.Text = "نام کاربر:", .Location = New Point(20, 30), .Size = New Size(100, 20), .RightToLeft = RightToLeft.Yes}
        Dim lblNumber As New Label() With {.Text = "عدد:", .Location = New Point(20, 80), .Size = New Size(100, 20), .RightToLeft = RightToLeft.Yes}
        Dim lblIPAddress As New Label() With {.Text = "آدرس IP:", .Location = New Point(20, 130), .Size = New Size(100, 20), .RightToLeft = RightToLeft.Yes}
        Me.Controls.AddRange({lblUserName, lblNumber, lblIPAddress})

        ' راه‌اندازی ML.NET
        mlContext = New MLContext()
        TrainMLModel()

        ' راه‌اندازی سرور SignalR
        Task.Run(Sub() StartSignalRServer())
        InitializeSignalRClient()

        ' بارگذاری تنظیمات API
        LoadApiSettings()
    End Sub

    Private Sub TrainMLModel()
        ' داده‌های واقعی‌تر برای آموزش مدل
        Dim data As New List(Of NetworkData) From {
            New NetworkData With {.Lat = 35.6892, .Lon = 51.3890, .HasMiningPorts = True, .IsMiner = True}, ' تهران، ماینر
            New NetworkData With {.Lat = 37.7510, .Lon = -122.4194, .HasMiningPorts = False, .IsMiner = False}, ' گوگل، غیرماینر
            New NetworkData With {.Lat = 51.5074, .Lon = -0.1278, .HasMiningPorts = True, .IsMiner = True}, ' لندن، ماینر
            New NetworkData With {.Lat = 40.7128, .Lon = -74.0060, .HasMiningPorts = False, .IsMiner = False}, ' نیویورک، غیرماینر
            New NetworkData With {.Lat = 55.7558, .Lon = 37.6173, .HasMiningPorts = True, .IsMiner = True}, ' مسکو، ماینر
            New NetworkData With {.Lat = 34.0522, .Lon = -118.2437, .HasMiningPorts = False, .IsMiner = False}, ' لس‌آنجلس، غیرماینر
            New NetworkData With {.Lat = 48.8566, .Lon = 2.3522, .HasMiningPorts = True, .IsMiner = True}, ' پاریس، ماینر
            New NetworkData With {.Lat = 35.6762, .Lon = 139.6503, .HasMiningPorts = False, .IsMiner = False}, ' توکیو، غیرماینر
            New NetworkData With {.Lat = 39.9042, .Lon = 116.4074, .HasMiningPorts = True, .IsMiner = True}, ' پکن، ماینر
            New NetworkData With {.Lat = -33.8688, .Lon = 151.2093, .HasMiningPorts = False, .IsMiner = False}, ' سیدنی، غیرماینر
            New NetworkData With {.Lat = 25.2048, .Lon = 55.2708, .HasMiningPorts = True, .IsMiner = True}, ' دبی، ماینر
            New NetworkData With {.Lat = 19.4326, .Lon = -99.1332, .HasMiningPorts = False, .IsMiner = False}, ' مکزیکوسیتی، غیرماینر
            New NetworkData With {.Lat = -23.5505, .Lon = -46.6333, .HasMiningPorts = True, .IsMiner = True}, ' سائوپائولو، ماینر
            New NetworkData With {.Lat = 1.3521, .Lon = 103.8198, .HasMiningPorts = False, .IsMiner = False}, ' سنگاپور، غیرماینر
            New NetworkData With {.Lat = 59.3293, .Lon = 18.0686, .HasMiningPorts = True, .IsMiner = True}, ' استکهلم، ماینر
            New NetworkData With {.Lat = 52.5200, .Lon = 13.4050, .HasMiningPorts = False, .IsMiner = False}, ' برلین، غیرماینر
            New NetworkData With {.Lat = 28.6139, .Lon = 77.2090, .HasMiningPorts = True, .IsMiner = True}, ' دهلی، ماینر
            New NetworkData With {.Lat = 41.9028, .Lon = 12.4964, .HasMiningPorts = False, .IsMiner = False}, ' رم، غیرماینر
            New NetworkData With {.Lat = 43.6532, .Lon = -79.3832, .HasMiningPorts = True, .IsMiner = True}, ' تورنتو، ماینر
            New NetworkData With {.Lat = -34.6037, .Lon = -58.3816, .HasMiningPorts = False, .IsMiner = False} ' بوئنوس آیرس، غیرماینر
        }
        Dim dataView = mlContext.Data.LoadFromEnumerable(data)
        Dim pipeline = mlContext.Transforms.Concatenate("Features", "Lat", "Lon", "HasMiningPorts").
            Append(mlContext.BinaryClassification.Trainers.FastTree())
        model = pipeline.Fit(dataView)
    End Sub

    Private Function EncryptData(data As String) As String
        Using aes As New AesManaged()
            aes.Key = Encoding.UTF8.GetBytes(AES_KEY)
            aes.IV = New Byte(15) {}
            Dim encryptor = aes.CreateEncryptor(aes.Key, aes.IV)
            Using ms As New MemoryStream()
                Using cs As New CryptoStream(ms, encryptor, CryptoStreamMode.Write)
                    Using sw As New StreamWriter(cs)
                        sw.Write(data)
                    End Using
                End Using
                Return Convert.ToBase64String(ms.ToArray())
            End Using
        End Using
    End Function

    Private Function DecryptData(data As String) As String
        Try
            Using aes As New AesManaged()
                aes.Key = Encoding.UTF8.GetBytes(AES_KEY)
                aes.IV = New Byte(15) {}
                Dim decryptor = aes.CreateDecryptor(aes.Key, aes.IV)
                Using ms As New MemoryStream(Convert.FromBase64String(data))
                    Using cs As New CryptoStream(ms, decryptor, CryptoStreamMode.Read)
                        Using sr As New StreamReader(cs)
                            Return sr.ReadToEnd()
                        End Using
                    End Using
                End Using
            End Using
        Catch
            Return String.Empty
        End Try
    End Function

    Private Async Sub StartSignalRServer()
        Dim builder = WebApplication.CreateBuilder()
        builder.Services.AddSignalR()
        Dim app = builder.Build()
        app.MapHub(Of ChatHub)("/chatHub")
        Await app.RunAsync("http://localhost:5000")
    End Sub

    Private Async Sub InitializeSignalRClient()
        hubConnection = New HubConnectionBuilder().WithUrl("http://localhost:5000/chatHub").Build()
        AddHandler hubConnection.On(Of String)("ReceiveMessage", Sub(message)
                                                                    txtChat.AppendText(message & vbCrLf)
                                                                End Sub)
        Try
            Await hubConnection.StartAsync()
            txtChat.AppendText("ربات متصل شد! خوش آمدید!" & vbCrLf)
        Catch ex As Exception
            txtChat.AppendText("خطا در اتصال به ربات: " & ex.Message & vbCrLf)
        End Try
    End Sub

    Private Sub LoadApiSettings()
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "api_settings.json")
            If File.Exists(filePath) Then
                Dim settings = JsonConvert.DeserializeObject(Of Dictionary(Of String, String))(File.ReadAllText(filePath))
                XAI_API_KEY = settings("xaiApiKey")
            End If
        Catch
            ' نادیده گرفتن خطا
        End Try
    End Sub

    Private Sub SaveApiSettings()
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "api_settings.json")
            Dim settings = New Dictionary(Of String, String) From {{"xaiApiKey", XAI_API_KEY}}
            File.WriteAllText(filePath, JsonConvert.SerializeObject(settings))
        Catch ex As Exception
            MessageBox.Show("خطا در ذخیره تنظیمات API: " & ex.Message, "خطا", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Async Sub btnSendChat_Click(sender As Object, e As EventArgs) Handles btnSendChat.Click
        Dim message As String = txtChat.Text.Trim()
        If Not String.IsNullOrEmpty(message) Then
            Try
                Dim client As New WebClient()
                client.Headers.Add("Authorization", "Bearer " & XAI_API_KEY)
                Dim response = client.UploadString("https://x.ai/api/chat", "POST", JsonConvert.SerializeObject(New With {.message = message}))
                Dim responseObj = JsonConvert.DeserializeObject(Of Dictionary(Of String, String))(response)
                txtChat.AppendText("ربات: " & responseObj("response") & vbCrLf)
                Await hubConnection.InvokeAsync("SendMessage", message)
            Catch ex As Exception
                txtChat.AppendText("خطا در چت: " & ex.Message & vbCrLf)
            End Try
        End If
    End Sub

    Private Sub btnExportCsv_Click(sender As Object, e As EventArgs) Handles btnExportCsv.Click
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "report_" & DateTime.Now.ToString("yyyyMMdd_HHmmss") & ".csv")
            Dim csv As String = "Timestamp,UserName,Number,IPAddress,NetworkInfo,NmapResult,SuricataLogs,IsMiner" & vbCrLf
            Dim logPath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "user_data.json")
            If File.Exists(logPath) Then
                Dim lines = File.ReadAllLines(logPath)
                For Each line In lines
                    Dim decrypted = DecryptData(line)
                    If Not String.IsNullOrEmpty(decrypted) Then
                        Dim data = JsonConvert.DeserializeObject(Of Dictionary(Of String, String))(decrypted)
                        csv &= $"{data("timestamp")},{data("userName")},{data("number")},{data("ipAddress")},{data("networkInfo").Replace(",", ";")},{data("nmapResult").Replace(",", ";")},{data("suricataLogs").Replace(",", ";")},{data("isMiner")}" & vbCrLf
                    End If
                Next
                File.WriteAllText(filePath, csv)
                MessageBox.Show("خروجی CSV در " & filePath & " ذخیره شد.", "خروجی", MessageBoxButtons.OK, MessageBoxIcon.Information)
            Else
                MessageBox.Show("فایل لاگ یافت نشد.", "خروجی", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            End If
        Catch ex As Exception
            MessageBox.Show("خطا در تولید خروجی CSV: " & ex.Message, "خطا", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub btnExportPdf_Click(sender As Object, e As EventArgs) Handles btnExportPdf.Click
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "report_" & DateTime.Now.ToString("yyyyMMdd_HHmmss") & ".pdf")
            Using writer As New PdfWriter(filePath)
                Using pdf As New PdfDocument(writer)
                    Dim document As New Document(pdf)
                    document.Add(New Paragraph("گزارش سیستم تشخیص ماینر").SetTextAlignment(iText.Layout.Properties.TextAlignment.CENTER))
                    document.Add(New Paragraph("زمان: " & DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")))
                    document.Add(New Paragraph("تعداد کاربران: " & userList.Count))
                    Dim table As New Table(8)
                    table.AddHeaderCell("زمان")
                    table.AddHeaderCell("نام کاربر")
                    table.AddHeaderCell("عدد")
                    table.AddHeaderCell("آدرس IP")
                    table.AddHeaderCell("اطلاعات شبکه")
                    table.AddHeaderCell("نتایج nmap")
                    table.AddHeaderCell("لاگ‌های Suricata")
                    table.AddHeaderCell("ماینر")
                    Dim logPath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "user_data.json")
                    If File.Exists(logPath) Then
                        Dim lines = File.ReadAllLines(logPath)
                        For Each line In lines
                            Dim decrypted = DecryptData(line)
                            If Not String.IsNullOrEmpty(decrypted) Then
                                Dim data = JsonConvert.DeserializeObject(Of Dictionary(Of String, String))(decrypted)
                                table.AddCell(data("timestamp"))
                                table.AddCell(data("userName"))
                                table.AddCell(data("number"))
                                table.AddCell(data("ipAddress"))
                                table.AddCell(data("networkInfo"))
                                table.AddCell(data("nmapResult"))
                                table.AddCell(data("suricataLogs"))
                                table.AddCell(data("isMiner"))
                            End If
                        Next
                    End If
                    document.Add(table)
                    document.Close()
                End Using
            End Using
            MessageBox.Show("خروجی PDF در " & filePath & " ذخیره شد.", "خروجی", MessageBoxButtons.OK, MessageBoxIcon.Information)
        Catch ex As Exception
            MessageBox.Show("خطا در تولید خروجی PDF: " & ex.Message, "خطا", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub btnSubmit_Click(sender As Object, e As EventArgs) Handles btnSubmit.Click
        Dim output As String = ""
        Dim userName As String = txtUserName.Text.Trim()
        Dim input As String = txtNumber.Text.Trim()
        Dim ipAddress As String = txtIPAddress.Text.Trim()
        Dim networkInfo As String = ""
        Dim nmapResult As String = "N/A"
        Dim suricataLogs As String = "[]"
        Dim isMiner As String = "N/A"

        ' خوش‌آمدگویی
        If String.IsNullOrEmpty(userName) Then
            output &= "نامی وارد نشده، خوش‌آمد به کاربر ناشناس!" & vbCrLf
        Else
            output &= "سلام، " & userName & "! به این برنامه ویژوال بیسیک خوش آمدید!" & vbCrLf
        End If

        ' بررسی زوج یا فرد بودن عدد
        Dim number As Integer
        If Integer.TryParse(input, number) Then
            output &= If(number Mod 2 = 0, "عدد " & number & " زوج است!" & vbCrLf, "عدد " & number & " فرد است!" & vbCrLf)
        Else
            output &= "ورودی نامعتبر! لطفاً یک عدد معتبر وارد کنید." & vbCrLf
        End If

        ' بررسی آدرس IP
        Dim ipRegex As String = "^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        If Not Regex.IsMatch(ipAddress, ipRegex) Then
            output &= "آدرس IP نامعتبر است!" & vbCrLf
            networkInfo = "{""status"": ""fail"", ""message"": ""Invalid IP address""}"
        Else
            ' دریافت اطلاعات شبکه از ip-api.com
            Try
                Dim client As New WebClient()
                networkInfo = client.DownloadString("https://ip-api.com/json/" & ipAddress & "?fields=status,country,city,lat,lon,isp,org")
                output &= "اطلاعات شبکه دریافت شد: " & networkInfo & vbCrLf
            Catch ex As Exception
                output &= "خطا در دریافت اطلاعات شبکه: " & ex.Message & vbCrLf
                networkInfo = "{""status"": ""fail"", ""message"": """ & ex.Message & """}"
            End Try

            ' تحلیل آفلاین با ML.NET
            Try
                Dim networkInfoObj = JsonConvert.DeserializeObject(Of Dictionary(Of String, Object))(networkInfo)
                If networkInfoObj("status").ToString() = "success" Then
                    Dim predictionEngine = mlContext.Model.CreatePredictionEngine(Of NetworkData, NetworkDataPrediction)(model)
                    Dim inputData As New NetworkData With {
                        .Lat = Convert.ToSingle(networkInfoObj("lat")),
                        .Lon = Convert.ToSingle(networkInfoObj("lon")),
                        .HasMiningPorts = chkNmap.Checked AndAlso nmapResult.Contains("open")
                    }
                    Dim prediction = predictionEngine.Predict(inputData)
                    isMiner = If(prediction.IsMiner, "ماینر", "غیر ماینر")
                    output &= "تحلیل آفلاین ماینر: " & isMiner & vbCrLf

                    ' به‌روزرسانی نمودار
                    chart.Series("IPLocations").Points.AddXY(inputData.Lon, inputData.Lat)
                    chart.Series("IPLocations").Points.Last().MarkerStyle = If(prediction.IsMiner, MarkerStyle.Circle, MarkerStyle.Square)
                    chart.Series("IPLocations").Points.Last().MarkerColor = If(prediction.IsMiner, Color.Red, Color.Green)
                End If
            Catch ex As Exception
                output &= "خطا در تحلیل آفلاین: " & ex.Message & vbCrLf
            End Try

            ' تحلیل بلادرنگ با xAI API
            Try
                Dim client As New WebClient()
                client.Headers.Add("Authorization", "Bearer " & XAI_API_KEY)
                Dim analysisData = JsonConvert.SerializeObject(New With {.ip = ipAddress, .networkInfo = networkInfo})
                Dim analysisResponse = client.UploadString("https://x.ai/api/analyze", "POST", analysisData)
                Dim analysisResult = JsonConvert.DeserializeObject(Of Dictionary(Of String, String))(analysisResponse)
                output &= "تحلیل بلادرنگ ماینر: " & analysisResult("result") & vbCrLf
            Catch ex As Exception
                output &= "خطا در تحلیل بلادرنگ: " & ex.Message & vbCrLf
            End Try

            ' اسکن nmap
            If chkNmap.Checked Then
                Try
                    Dim process As New Process()
                    process.StartInfo.FileName = "nmap.exe"
                    process.StartInfo.Arguments = $"-p {networkSettings("ports")} --open {ipAddress}"
                    process.StartInfo.RedirectStandardOutput = True
                    process.StartInfo.UseShellExecute = False
                    process.StartInfo.CreateNoWindow = True
                    process.Start()
                    nmapResult = process.StandardOutput.ReadToEnd()
                    process.WaitForExit()
                    output &= If(nmapResult.Contains("open"), "دستگاه ممکن است ماینر باشد (پورت‌های باز: " & nmapResult & ")" & vbCrLf, "هیچ پورت ماینینگی باز نیست." & vbCrLf)
                Catch ex As Exception
                    output &= "خطا در اسکن پورت‌ها: " & ex.Message & vbCrLf
                    nmapResult = "N/A"
                End Try
            End If

            ' دریافت لاگ‌های Suricata
            If chkSuricata.Checked Then
                Try
                    Dim client As New WebClient()
                    suricataLogs = client.DownloadString("http://localhost:5000/logs")
                    output &= "لاگ‌های اسکن Suricata دریافت شد." & vbCrLf
                Catch ex As Exception
                    output &= "خطا در دریافت لاگ‌های Suricata: " & ex.Message & vbCrLf
                    suricataLogs = "[]"
                End Try
            End If
        End If

        ' ذخیره داده‌ها
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "user_data.json")
            Dim dataToSave As String = "{" & _
                """timestamp"": """ & DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") & """," & _
                """userName"": """ & userName.Replace("""", "\""") & """," & _
                """number"": """ & input & """," & _
                """ipAddress"": """ & ipAddress & """," & _
                """networkInfo"": " & networkInfo & "," & _
                """nmapResult"": """ & nmapResult.Replace("""", "\""") & """," & _
                """suricataLogs"": " & suricataLogs & "," & _
                """isMiner"": """ & isMiner & """" & _
                "}"
            Dim encryptedData = EncryptData(dataToSave)
            File.AppendAllText(filePath, encryptedData & Environment.NewLine)
            output &= "داده‌ها با موفقیت در فایل " & filePath & " ذخیره شدند." & vbCrLf
        Catch ex As Exception
            output &= "خطا در ذخیره داده‌ها: " & ex.Message & vbCrLf
        End Try

        txtOutput.Text = output
    End Sub

    ' رویدادهای منو
    Private Sub MenuAddUser_Click(sender As Object, e As EventArgs)
        Dim newUser As String = InputBox("نام کاربر جدید را وارد کنید:", "افزودن کاربر")
        If Not String.IsNullOrEmpty(newUser) Then
            userList.Add(newUser)
            SaveUsers()
            MessageBox.Show("کاربر " & newUser & " اضافه شد.", "مدیریت", MessageBoxButtons.OK, MessageBoxIcon.Information)
        End If
    End Sub

    Private Sub MenuRemoveUser_Click(sender As Object, e As EventArgs)
        Dim userToRemove As String = InputBox("نام کاربر برای حذف را وارد کنید:", "حذف کاربر")
        If userList.Contains(userToRemove) Then
            userList.Remove(userToRemove)
            SaveUsers()
            MessageBox.Show("کاربر " & userToRemove & " حذف شد.", "مدیریت", MessageBoxButtons.OK, MessageBoxIcon.Information)
        Else
            MessageBox.Show("کاربر یافت نشد.", "مدیریت", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        End If
    End Sub

    Private Sub MenuLogs_Click(sender As Object, e As EventArgs)
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "user_data.json")
            If File.Exists(filePath) Then
                Dim logs As String = ""
                Dim lines = File.ReadAllLines(filePath)
                For Each line In lines
                    Dim decrypted = DecryptData(line)
                    If Not String.IsNullOrEmpty(decrypted) Then
                        logs &= decrypted & vbCrLf
                    End If
                Next
                MessageBox.Show("لاگ‌ها:" & vbCrLf & logs, "نمایش لاگ‌ها", MessageBoxButtons.OK, MessageBoxIcon.Information)
            Else
                MessageBox.Show("فایل لاگ یافت نشد.", "نمایش لاگ‌ها", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            End If
        Catch ex As Exception
            MessageBox.Show("خطا در نمایش لاگ‌ها: " & ex.Message, "نمایش لاگ‌ها", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub MenuDatabase_Click(sender As Object, e As EventArgs)
        Dim dbForm As New Form() With {
            .Text = "مدیریت پایگاه داده کاربران",
            .Size = New Size(400, 300),
            .FormBorderStyle = FormBorderStyle.FixedSingle,
            .MaximizeBox = False,
            .RightToLeft = RightToLeft.Yes
        }
        Dim lstUsers As New ListBox() With {.Location = New Point(20, 20), .Size = New Size(340, 200)}
        For Each user In userList
            lstUsers.Items.Add(user)
        Next
        Dim btnClose As New Button() With {.Text = "بستن", .Location = New Point(20, 230), .Size = New Size(100, 30)}
        AddHandler btnClose.Click, Sub() dbForm.Close()
        dbForm.Controls.AddRange({lstUsers, btnClose})
        dbForm.ShowDialog()
    End Sub

    Private Sub MenuReports_Click(sender As Object, e As EventArgs)
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "report.txt")
            Dim report As String = "گزارش سیستم تشخیص ماینر" & vbCrLf & _
                                  "زمان: " & DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") & vbCrLf & _
                                  "تعداد کاربران: " & userList.Count & vbCrLf & _
                                  "لاگ‌های اخیر:" & vbCrLf
            Dim logPath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "user_data.json")
            If File.Exists(logPath) Then
                Dim lines = File.ReadAllLines(logPath)
                For Each line In lines
                    Dim decrypted = DecryptData(line)
                    If Not String.IsNullOrEmpty(decrypted) Then
                        report &= decrypted & vbCrLf
                    End If
                Next
            End If
            File.WriteAllText(filePath, report)
            MessageBox.Show("گزارش در " & filePath & " ذخیره شد.", "تولید گزارش", MessageBoxButtons.OK, MessageBoxIcon.Information)
        Catch ex As Exception
            MessageBox.Show("خطا در تولید گزارش: " & ex.Message, "تولید گزارش", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub

    Private Sub MenuQuickScan_Click(sender As Object, e As EventArgs)
        txtIPAddress.Text = networkSettings("defaultIP")
        chkNmap.Checked = True
        btnSubmit.PerformClick()
    End Sub

    Private Sub MenuFullScan_Click(sender As Object, e As EventArgs)
        txtIPAddress.Text = networkSettings("defaultIP")
        chkNmap.Checked = True
        chkSuricata.Checked = True
        btnSubmit.PerformClick()
    End Sub

    Private Sub MenuRealtimeAnalysis_Click(sender As Object, e As EventArgs)
        If String.IsNullOrEmpty(txtIPAddress.Text) Then
            MessageBox.Show("لطفاً یک آدرس IP وارد کنید.", "تحلیل بلادرنگ", MessageBoxButtons.OK, MessageBoxIcon.Warning)
            Return
        End If
        Try
            Dim client As New WebClient()
            client.Headers.Add("Authorization", "Bearer " & XAI_API_KEY)
            Dim analysisData = JsonConvert.SerializeObject(New With {.ip = txtIPAddress.Text})
            Dim analysisResponse = client.UploadString("https://x.ai/api/analyze", "POST", analysisData)
            Dim analysisResult = JsonConvert.DeserializeObject(Of Dictionary(Of String, String))(analysisResponse)
            txtOutput.Text = "تحلیل بلادرنگ ماینر: " & analysisResult("result") & vbCrLf
        Catch ex As Exception
            txtOutput.Text = "خطا در تحلیل بلادرنگ: " & ex.Message & vbCrLf
        End Try
    End Sub

    Private Sub MenuOfflineAnalysis_Click(sender As Object, e As EventArgs)
        btnSubmit.PerformClick()
    End Sub

    Private Sub MenuNetworkSettings_Click(sender As Object, e As EventArgs)
        Dim settingsForm As New Form() With {
            .Text = "تنظیمات شبکه",
            .Size = New Size(400, 200),
            .FormBorderStyle = FormBorderStyle.FixedSingle,
            .MaximizeBox = False,
            .RightToLeft = RightToLeft.Yes
        }
        Dim txtDefaultIP As New TextBox() With {.Location = New Point(20, 50), .Size = New Size(200, 25), .Text = networkSettings("defaultIP")}
        Dim txtPorts As New TextBox() With {.Location = New Point(20, 100), .Size = New Size(200, 25), .Text = networkSettings("ports")}
        Dim btnSave As New Button() With {.Text = "ذخیره", .Location = New Point(20, 130), .Size = New Size(100, 30)}
        Dim lblDefaultIP As New Label() With {.Text = "IP پیش‌فرض:", .Location = New Point(20, 30), .Size = New Size(100, 20)}
        Dim lblPorts As New Label() With {.Text = "پورت‌ها:", .Location = New Point(20, 80), .Size = New Size(100, 20)}
        AddHandler btnSave.Click, Sub()
                                      networkSettings("defaultIP") = txtDefaultIP.Text
                                      networkSettings("ports") = txtPorts.Text
                                      settingsForm.Close()
                                  End Sub
        settingsForm.Controls.AddRange({txtDefaultIP, txtPorts, btnSave, lblDefaultIP, lblPorts})
        settingsForm.ShowDialog()
    End Sub

    Private Sub MenuApiSettings_Click(sender As Object, e As EventArgs)
        Dim apiForm As New Form() With {
            .Text = "تنظیمات API",
            .Size = New Size(400, 150),
            .FormBorderStyle = FormBorderStyle.FixedSingle,
            .MaximizeBox = False,
            .RightToLeft = RightToLeft.Yes
        }
        Dim txtApiKey As New TextBox() With {.Location = New Point(20, 50), .Size = New Size(200, 25), .Text = XAI_API_KEY}
        Dim btnSave As New Button() With {.Text = "ذخیره", .Location = New Point(20, 80), .Size = New Size(100, 30)}
        Dim lblApiKey As New Label() With {.Text = "کلید xAI API:", .Location = New Point(20, 30), .Size = New Size(100, 20)}
        AddHandler btnSave.Click, Sub()
                                      XAI_API_KEY = txtApiKey.Text
                                      SaveApiSettings()
                                      apiForm.Close()
                                  End Sub
        apiForm.Controls.AddRange({txtApiKey, btnSave, lblApiKey})
        apiForm.ShowDialog()
    End Sub

    Private Sub SaveUsers()
        Try
            Dim filePath As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "users.json")
            File.WriteAllText(filePath, JsonConvert.SerializeObject(userList))
        Catch ex As Exception
            MessageBox.Show("خطا در ذخیره کاربران: " & ex.Message, "خطا", MessageBoxButtons.OK, MessageBoxIcon.Error)
        End Try
    End Sub
End Class

Module MinerDetector
    Sub Main()
        Application.Run(New MinerDetectorForm())
    End Sub
End Module