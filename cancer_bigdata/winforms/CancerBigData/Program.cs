using System;
using System.Windows.Forms;
using CancerBigData.UI;

namespace CancerBigData
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            ApplicationConfiguration.Initialize();
            Application.Run(new MainForm());
        }
    }
}
