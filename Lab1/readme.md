测量日光灯时，由于拍摄角度问题，没有把部分蓝色的光谱拍进去，导致光谱蓝色一端有部分被截断。而蓝色部分有汞的尖锐的发射线，本可以用来标定波长。

于是退而求其次，通过红色和绿色波段的发射线标定波长。

我写了好几个代码脚本。阅读它可以知道我的开发流程。一开始通过互相之间的比对和手动调整来完成光谱相互对齐（通过调节scale offset 和intensity参数），但是由于缺少参比无法获得正确波长；

后来我在wikimedia上面找到了一个光谱图片，使用Engauge Digitizer完成了数字化，保存为reference\_spectrum.

然后我应用相同的逻辑完成了对齐

为了方便对齐操作，我做出了如下改进：
1.将采样线映射到200-900nm，这样光谱一开始的范围就不会受到分辨率的影响（我的几幅照片分辨率差别很大）

2\.将缩放的中心（anchor，锚点）设为520nm，这样缩放的时候就无需大范围调整offset

3.intensity自动按照最强峰进行归一化，方便互相比对

最终得到了光谱图像。仔细观察数据我发现在绿色波段有两个靠得很近的峰可以被区分开：
Peak number	Wavelength of peak (nm)	Species producing peak	Actual line location (nm)
4 542.4 terbium from Tb3+ ~543 to 544
5 546.5 mercury 546.074

数据来源：wikimedia
Spectrum with peaks labelled taken with an Ocean Optics HR2000 spectrometer [1] of ambient light provided by fluorescent lamps. Spectrum taken by me (apparently en:user:Deglr6328). The spectrometer appears to be about ~.6 to .8 nm off judging from the location of known peaks. Interpretation of spectral peaks has been done using the NIST database of spectra for mercury [2] and an article on fluorescent light phosphors [3]. This spectrum is not calibrated for intensity.

我把具体的图像保存到了
fluorescent_lamp_spectra_aligned_scaled_norm_detail_at_550nm.jpg
可以发现在蓝色通道这两个峰被成功区分开了，证明我的光谱仪理论分辨率可以达到3nm


