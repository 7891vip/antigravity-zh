using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace AntigravityZH
{
    internal static class Program
    {
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern bool SetProcessDPIAware();

        [STAThread]
        private static void Main(string[] args)
        {
            // 高分屏下按系统 DPI 渲染，避免整个窗口被位图拉伸导致字体发虚
            try { SetProcessDPIAware(); } catch { }

            string mode = "";
            foreach (string a in args)
            {
                string s = a.ToLowerInvariant();
                if (s == "--install" || s == "/install") mode = "install";
                else if (s == "--restore" || s == "/restore") mode = "restore";
                else if (s == "--status" || s == "/status") mode = "status";
                else if (s == "--help" || s == "/?" || s == "-h") mode = "help";
            }

            if (mode == "help")
            {
                MessageBox.Show(
                    "Antigravity 简体中文汉化工具\n\n" +
                    "  双击运行            打开图形界面\n" +
                    "  --install           静默安装/更新汉化\n" +
                    "  --restore           静默还原官方英文\n" +
                    "  --status            仅检测状态并写入日志\n\n" +
                    "日志：%TEMP%\\antigravity-zh.log",
                    "帮助", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            if (mode.Length > 0)
            {
                int code = SilentRunner.Run(mode);
                Environment.Exit(code);
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    internal static class Paths
    {
        public static readonly string LogFile =
            Path.Combine(Path.GetTempPath(), "antigravity-zh.log");

        public static void Log(string msg)
        {
            try
            {
                File.AppendAllText(LogFile,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + msg + Environment.NewLine,
                    Encoding.UTF8);
            }
            catch { }
        }

        public static string FindApp()
        {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string pf = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            string pf86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);

            string[] cands = new string[] {
                Path.Combine(local, @"Programs\antigravity"),
                Path.Combine(pf, "Antigravity"),
                Path.Combine(pf86, "Antigravity")
            };
            foreach (string c in cands)
            {
                if (!string.IsNullOrEmpty(c) && File.Exists(Path.Combine(c, @"resources\app.asar")))
                    return c;
            }

            string[] roots = new string[] {
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            };
            RegistryKey[] hives = new RegistryKey[] { Registry.LocalMachine, Registry.CurrentUser };
            foreach (RegistryKey hive in hives)
            {
                foreach (string root in roots)
                {
                    try
                    {
                        using (RegistryKey k = hive.OpenSubKey(root))
                        {
                            if (k == null) continue;
                            foreach (string name in k.GetSubKeyNames())
                            {
                                using (RegistryKey sub = k.OpenSubKey(name))
                                {
                                    if (sub == null) continue;
                                    object dn = sub.GetValue("DisplayName");
                                    object loc = sub.GetValue("InstallLocation");
                                    if (dn == null || loc == null) continue;
                                    if (dn.ToString().IndexOf("Antigravity", StringComparison.OrdinalIgnoreCase) < 0) continue;
                                    string p = loc.ToString().TrimEnd('\\');
                                    if (File.Exists(Path.Combine(p, @"resources\app.asar")))
                                        return p;
                                }
                            }
                        }
                    }
                    catch { }
                }
            }
            return null;
        }

        public static string Ajar(string appDir) { return Path.Combine(appDir, @"resources\app.asar"); }
        public static string Backup(string appDir) { return Path.Combine(appDir, @"resources\app.asar.zh-backup"); }
    }

    internal static class Payload
    {
        private static string ResourceText(string name)
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream(name))
            {
                if (s == null) throw new InvalidOperationException("缺少内嵌资源: " + name);
                using (StreamReader r = new StreamReader(s, Encoding.UTF8))
                    return r.ReadToEnd();
            }
        }

        public static string ManifestValue(string key)
        {
            string json = ResourceText("manifest.json");
            string needle = "\"" + key + "\"";
            int i = json.IndexOf(needle, StringComparison.Ordinal);
            if (i < 0) return "";
            i = json.IndexOf(':', i + needle.Length);
            if (i < 0) return "";
            i = json.IndexOf('"', i);
            if (i < 0) return "";
            int j = json.IndexOf('"', i + 1);
            if (j < 0) return "";
            return json.Substring(i + 1, j - i - 1);
        }

        public static string ExtractToTemp()
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream("payload.asar"))
            {
                if (s == null) throw new InvalidOperationException("缺少内嵌资源: payload.asar");
                string tmp = Path.Combine(Path.GetTempPath(), "antigravity-zh-" + Guid.NewGuid().ToString("N") + ".asar");
                using (FileStream fs = new FileStream(tmp, FileMode.Create, FileAccess.Write))
                    s.CopyTo(fs);
                return tmp;
            }
        }
    }

    internal static class Core
    {
        public static string Sha256(string path)
        {
            using (SHA256 sha = SHA256.Create())
            using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                byte[] hash = sha.ComputeHash(fs);
                StringBuilder sb = new StringBuilder();
                foreach (byte b in hash) sb.Append(b.ToString("x2"));
                return sb.ToString();
            }
        }

        public static void KillApp(Action<string> log)
        {
            Process[] ps = Process.GetProcessesByName("Antigravity");
            Process[] ls = Process.GetProcessesByName("language_server");
            if (ps.Length == 0 && ls.Length == 0) return;
            log("正在关闭 Antigravity（共 " + ps.Length + " 个进程）…");
            foreach (Process p in ps)
            {
                try { p.Kill(); } catch { }
            }
            foreach (Process p in ls)
            {
                try { p.Kill(); } catch { }
            }
            for (int i = 0; i < 30; i++)
            {
                Thread.Sleep(300);
                if (Process.GetProcessesByName("Antigravity").Length == 0
                    && Process.GetProcessesByName("language_server").Length == 0) break;
            }
            // 给 Chromium 释放 userData 锁与 socket 的时间，否则紧接着启动的新实例会自行退出
            Thread.Sleep(2500);
        }

        public static bool IsRunning()
        {
            return Process.GetProcessesByName("Antigravity").Length > 0;
        }

        public static void StartApp(string appDir)
        {
            string exe = Path.Combine(appDir, "Antigravity.exe");
            if (!File.Exists(exe)) return;
            for (int attempt = 0; attempt < 3; attempt++)
            {
                if (IsRunning()) return;
                if (attempt > 0)
                {
                    Thread.Sleep(4000);
                    if (IsRunning()) return;
                }
                ProcessStartInfo psi = new ProcessStartInfo(exe);
                psi.WorkingDirectory = appDir;
                psi.UseShellExecute = false;
                // 从 Electron 系终端（VS Code / 某些 IDE / CI）启动时可能继承该变量，
                // 会让 Antigravity 以 Node 模式启动后立即退出。
                try { psi.EnvironmentVariables.Remove("ELECTRON_RUN_AS_NODE"); } catch { }
                try { psi.EnvironmentVariables.Remove("ELECTRON_NO_ATTACH_CONSOLE"); } catch { }
                try { Process.Start(psi); } catch { }
                Thread.Sleep(2600);
            }
        }

        /// <summary>state: official / patched / other / missing</summary>
        public static string State(string asarPath, string packHash, string sourceHash)
        {
            if (!File.Exists(asarPath)) return "missing";
            string h = Sha256(asarPath);
            if (string.Equals(h, packHash, StringComparison.OrdinalIgnoreCase)) return "patched";
            if (string.Equals(h, sourceHash, StringComparison.OrdinalIgnoreCase)) return "official";
            return "other";
        }

        public static int Install(string appDir, Action<string> log)
        {
            string asar = Paths.Ajar(appDir);
            string bak = Paths.Backup(appDir);
            log("安装目录: " + appDir);

            KillApp(log);

            if (!File.Exists(bak))
            {
                File.Copy(asar, bak, true);
                log("已备份官方原版 → app.asar.zh-backup");
            }
            else
            {
                log("已存在官方备份，跳过备份");
            }

            string tmp = Payload.ExtractToTemp();
            try
            {
                File.Copy(tmp, asar, true);
            }
            finally
            {
                try { File.Delete(tmp); } catch { }
            }

            string want = Payload.ManifestValue("packAsarSha256");
            string got = Sha256(asar);
            if (want.Length > 0 && !string.Equals(want, got, StringComparison.OrdinalIgnoreCase))
            {
                log("校验失败，写入后哈希不一致！");
                return 2;
            }
            log("已写入汉化文件，SHA256 校验通过");
            StartApp(appDir);
            log("已启动 Antigravity");
            return 0;
        }

        public static int Restore(string appDir, Action<string> log)
        {
            string asar = Paths.Ajar(appDir);
            string bak = Paths.Backup(appDir);
            log("安装目录: " + appDir);
            if (!File.Exists(bak))
            {
                log("未找到备份 app.asar.zh-backup，无法还原");
                return 3;
            }
            KillApp(log);
            File.Copy(bak, asar, true);
            log("已还原官方原版 app.asar");
            StartApp(appDir);
            log("已启动 Antigravity");
            return 0;
        }
    }

    internal static class SilentRunner
    {
        public static int Run(string mode)
        {
            try
            {
                string app = Paths.FindApp();
                if (app == null)
                {
                    Paths.Log("未找到 Antigravity 安装目录");
                    return 4;
                }
                string packHash = Payload.ManifestValue("packAsarSha256");
                string sourceHash = Payload.ManifestValue("sourceAsarSha256");
                string state = Core.State(Paths.Ajar(app), packHash, sourceHash);
                Paths.Log("mode=" + mode + " app=" + app + " state=" + state);

                if (mode == "status") return 0;
                if (mode == "install")
                {
                    int rc = Core.Install(app, Paths.Log);
                    Paths.Log("install rc=" + rc);
                    return rc;
                }
                if (mode == "restore")
                {
                    int rc = Core.Restore(app, Paths.Log);
                    Paths.Log("restore rc=" + rc);
                    return rc;
                }
                return 0;
            }
            catch (Exception ex)
            {
                Paths.Log("异常: " + ex.ToString());
                return 1;
            }
        }
    }

    public class MainForm : Form
    {
        private Label _status;
        private TextBox _log;
        private Button _btnInstall;
        private Button _btnRestore;
        private Button _btnFolder;
        private string _appDir;

        public MainForm()
        {
            Text = "Antigravity 简体中文汉化工具";
            // 设计坐标按 96 DPI 计算，由 WinForms 按实际 DPI 等比放大，避免高分屏下被裁切
            AutoScaleDimensions = new SizeF(96F, 96F);
            AutoScaleMode = AutoScaleMode.Dpi;
            ClientSize = new Size(620, 470);
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            Font = new Font("Microsoft YaHei UI", 9f);

            Label title = new Label();
            title.Text = "Antigravity 简体中文汉化工具";
            title.Font = new Font("Microsoft YaHei UI", 14f, FontStyle.Bold);
            title.SetBounds(18, 14, 580, 30);
            Controls.Add(title);

            Label sub = new Label();
            sub.Text = "汉化包 v" + Payload.ManifestValue("version") +
                       "   ·   适用于 Antigravity " + Payload.ManifestValue("appVersion") +
                       "   ·   构建于 " + Payload.ManifestValue("builtAt");
            sub.ForeColor = Color.DimGray;
            sub.SetBounds(20, 46, 580, 20);
            Controls.Add(sub);

            GroupBox box = new GroupBox();
            box.Text = " 状态 ";
            box.SetBounds(16, 74, 588, 96);
            Controls.Add(box);

            _status = new Label();
            _status.SetBounds(14, 20, 560, 66);
            _status.Font = new Font("Microsoft YaHei UI", 9f);
            box.Controls.Add(_status);

            _btnInstall = new Button();
            _btnInstall.Text = "安装 / 更新汉化";
            _btnInstall.SetBounds(16, 182, 148, 34);
            _btnInstall.Click += new EventHandler(OnInstall);
            Controls.Add(_btnInstall);

            _btnRestore = new Button();
            _btnRestore.Text = "还原英文";
            _btnRestore.SetBounds(174, 182, 110, 34);
            _btnRestore.Click += new EventHandler(OnRestore);
            Controls.Add(_btnRestore);

            _btnFolder = new Button();
            _btnFolder.Text = "打开安装目录";
            _btnFolder.SetBounds(294, 182, 120, 34);
            _btnFolder.Click += new EventHandler(OnOpenFolder);
            Controls.Add(_btnFolder);

            LinkLabel link = new LinkLabel();
            link.Text = "GitHub 项目主页";
            link.SetBounds(452, 190, 140, 20);
            link.LinkClicked += new LinkLabelLinkClickedEventHandler(delegate (object s, LinkLabelLinkClickedEventArgs e)
            {
                try { Process.Start("https://github.com/7891vip/antigravity-zh"); } catch { }
            });
            Controls.Add(link);

            Label logTitle = new Label();
            logTitle.Text = "日志";
            logTitle.SetBounds(18, 226, 100, 18);
            Controls.Add(logTitle);

            _log = new TextBox();
            _log.Multiline = true;
            _log.ReadOnly = true;
            _log.ScrollBars = ScrollBars.Vertical;
            _log.SetBounds(16, 246, 588, 208);
            _log.BackColor = Color.FromArgb(248, 248, 250);
            _log.Font = new Font("Consolas", 8.5f);
            Controls.Add(_log);

            Load += new EventHandler(OnLoad);
        }

        private void Append(string msg)
        {
            _log.AppendText("[" + DateTime.Now.ToString("HH:mm:ss") + "] " + msg + Environment.NewLine);
            Paths.Log(msg);
        }

        private void OnLoad(object sender, EventArgs e)
        {
            Paths.Log("form dpi=" + DeviceDpi + " client=" + ClientSize.Width + "x" + ClientSize.Height
                      + " size=" + Size.Width + "x" + Size.Height);
            _appDir = Paths.FindApp();
            RefreshStatus();
            if (_appDir == null)
            {
                Append("未找到 Antigravity 安装目录，请手动选择。");
                ChooseFolder();
            }
            else
            {
                Append("已定位 Antigravity: " + _appDir);
            }
        }

        private void ChooseFolder()
        {
            using (FolderBrowserDialog d = new FolderBrowserDialog())
            {
                d.Description = "请选择 Antigravity 安装目录（其中包含 Antigravity.exe 与 resources 文件夹）";
                if (d.ShowDialog() == DialogResult.OK)
                {
                    if (File.Exists(Path.Combine(d.SelectedPath, @"resources\app.asar")))
                    {
                        _appDir = d.SelectedPath;
                        Append("已选择: " + _appDir);
                    }
                    else
                    {
                        MessageBox.Show("该目录下没有 resources\\app.asar，请重新选择。", "目录无效",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    }
                }
            }
            RefreshStatus();
        }

        private void RefreshStatus()
        {
            string packHash = Payload.ManifestValue("packAsarSha256");
            string sourceHash = Payload.ManifestValue("sourceAsarSha256");

            if (_appDir == null)
            {
                _status.Text = "安装目录：未找到\r\n状态：请点击「安装」后选择目录\r\n备份：—";
                return;
            }

            string asar = Paths.Ajar(_appDir);
            string bak = Paths.Backup(_appDir);
            string state = Core.State(asar, packHash, sourceHash);

            string stateText;
            if (state == "patched") stateText = "已汉化（中文界面）";
            else if (state == "official") stateText = "官方原版（英文界面）";
            else if (state == "missing") stateText = "未找到 app.asar";
            else stateText = "未知版本（客户端可能已升级）";

            string bakText = File.Exists(bak)
                ? "已备份（" + Math.Round(new FileInfo(bak).Length / 1048576.0, 2) + " MB）"
                : "尚未备份";

            string runText = Core.IsRunning() ? "，客户端正在运行" : "";
            _status.Text = "安装目录：" + _appDir + "\r\n"
                         + "当前状态：" + stateText + runText + "\r\n"
                         + "官方备份：" + bakText;
        }

        private void OnInstall(object sender, EventArgs e)
        {
            if (_appDir == null) { ChooseFolder(); if (_appDir == null) return; }

            if (Core.IsRunning())
            {
                if (MessageBox.Show("安装需要先关闭 Antigravity，安装完成后会自动重新启动。是否继续？",
                        "确认", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK)
                    return;
            }

            UseWaitCursor = true;
            _btnInstall.Enabled = false;
            try
            {
                int rc = Core.Install(_appDir, Append);
                if (rc == 0) Append("完成：界面已切换为简体中文。");
                else Append("安装失败，返回码 " + rc);
            }
            catch (Exception ex)
            {
                Append("安装异常: " + ex.Message);
            }
            finally
            {
                UseWaitCursor = false;
                _btnInstall.Enabled = true;
                RefreshStatus();
            }
        }

        private void OnRestore(object sender, EventArgs e)
        {
            if (_appDir == null) { ChooseFolder(); if (_appDir == null) return; }

            if (Core.IsRunning())
            {
                if (MessageBox.Show("还原需要先关闭 Antigravity，完成后会自动重新启动。是否继续？",
                        "确认", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK)
                    return;
            }

            UseWaitCursor = true;
            _btnRestore.Enabled = false;
            try
            {
                int rc = Core.Restore(_appDir, Append);
                if (rc == 0) Append("完成：已还原官方英文界面。");
                else if (rc == 3) MessageBox.Show("没有找到官方原版备份 app.asar.zh-backup，无法还原。",
                        "无法还原", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            catch (Exception ex)
            {
                Append("还原异常: " + ex.Message);
            }
            finally
            {
                UseWaitCursor = false;
                _btnRestore.Enabled = true;
                RefreshStatus();
            }
        }

        private void OnOpenFolder(object sender, EventArgs e)
        {
            if (_appDir == null) return;
            try { Process.Start(_appDir); } catch { }
        }
    }
}
