# -
一个简单的web屏幕中转共享程序，请勿商用

如您想将该工具用于商用，请查询相关被本工具调用的“库”或包括不限于任何形式存在于该工具代码中等
其他特殊的功能或情况，请自行查询官方网站或其他能够说明是否允许商用的公告或告示
本工具完全免费开源不收费，如商用者或其他有商用行为的人员因商用受到包括不限于侵权指控
法律控告等相关法律行为，与开发者无关，特此说明


if you intend to use this tool for commercial purposes, please check the relevant libraries called by this tool, as well as other special functions or scenarios contained in the tool’s code in any form or otherwise.
Please independently refer to the official website or other announcements/notices that specify whether commercial use is permitted.
This tool is completely free and open-source with no charges. The developer shall bear no liability for any legal actions including but not limited to infringement claims and legal prosecutions incurred by commercial users or any persons engaging in commercial activities related to the tool.
Hereby clarified.


            本程序采用：TCP+UDP双协议技术进行传输,在我们的系统中，TCP和UDP被分配了不同的职责：
            1.UDP（用户数据报协议） - 承担主要视频流传输任务
            核心作用： 负责传输实时的视频帧数据。
            优势： 由于视频流对少量丢包有一定容忍度（特别是经过压缩编码后），UDP的低延迟特性使得观众几乎可以实时看到屏幕上的变化，非常适合直播、远程演示等场景。

            2.TCP（传输控制协议） - 承担辅助控制和可靠性保障任务
            核心作用： 负责传输控制信息和关键元数据。
            优势： 利用其可靠的传输特性，确保重要指令和状态信息不丢失。

            3.总结
            确保重要指令和状态信息不丢失，主要是通过TCP协议传输以下关键信息：
            连接握手： 客户端连接后，服务器发送STREAM_OK_TCP，客户端回复READY，确保双方连接建立并准备就绪，此过程必须可靠。
            维持连接： TCP长连接本身可让服务器感知客户端是否在线，连接断开即刻可知。
            控制信息： 发送帧大小、帧序号等元数据（如send_tcp_control_info），这些小量但关键的信息若丢失会影响客户端同步，需TCP保证送达。
            TCP的可靠传输特性确保了这些基础通信流程的稳定，而视频数据则由UDP承载以保证低延迟。
