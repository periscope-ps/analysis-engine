import math
import matplotlib
matplotlib.use('Agg');
import matplotlib.pyplot as plt
from statsmodels.distributions.empirical_distribution import ECDF
import cbor2


def main():
   
    inputf = input("Input file: ")
    with open(inputf, "r") as input1:
         i = 0;
         ic = 0;
         line0 = input1.readline().strip();
         numd = 1.0;
         data = [0.0] * 100;
         while (line0 != ""):
             sl = line0.split(" ");
             ts = int(sl[0]);
             val = float(sl[1]);
             data[i] = val;
             i = int(math.fmod(i + 1, 100));
             if (math.fmod(numd, 100) == 0.0):
                cdf = ECDF(data);
                plt.plot(cdf.x, cdf.y, label="statmodels", 
                     marker="<", markerfacecolor='none');
                plt.legend();
                plt.title("CDF as a function of Data");
                plt.xlabel("data");
                plt.ylabel("cdf");
                ics = str(ic);
                plt.savefig("ecdf_" + ics + ".png");
                plt.close();
                ic = ic + 1;
             line0 = input1.readline().strip();
            
             numd = numd + 1;
                            


main()
