import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# Okabe-Ito
BLUE='#0072B2'; ORANGE='#E69F00'; GREEN='#009E73'; VERM='#D55E00'; PURPLE='#CC79A7'; SKY='#56B4E9'; BLACK='#000000'
MM=1/25.4
def setup(base=9):
    plt.rcParams.update({
        'font.family':'Liberation Sans',
        'mathtext.fontset':'custom',
        'mathtext.rm':'Liberation Sans','mathtext.it':'Liberation Sans:italic',
        'mathtext.bf':'Liberation Sans:bold','mathtext.sf':'Liberation Sans','mathtext.tt':'Liberation Sans','mathtext.cal':'Liberation Sans',
        'mathtext.default':'it',
        'font.size':base,'axes.labelsize':base+0.5,'axes.titlesize':base+1,
        'xtick.labelsize':base,'ytick.labelsize':base,'legend.fontsize':base-0.5,
        'axes.linewidth':0.7,'xtick.major.width':0.7,'ytick.major.width':0.7,
        'xtick.minor.width':0.5,'ytick.minor.width':0.5,
        'axes.grid':True,'grid.alpha':0.35,'grid.linewidth':0.5,
        'pdf.fonttype':42,'ps.fonttype':42,'axes.unicode_minus':True,
        'savefig.dpi':300,
    })
