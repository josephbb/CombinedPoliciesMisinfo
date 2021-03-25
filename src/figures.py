import pandas
import pickle
import matplotlib.pyplot as plt
import seaborn as sns
import pystan
import pandas as pd
import numpy as np
import numpy as np
import os
import glob
import string
import matplotlib.image as mpimg
import matplotlib.gridspec as gridspec
from src.utils import interp
from src.simulation import simulate

def plot_posterior(row, cumulative=True,freq=5,root='.'):
    sample_loc = root+'/output/posteriors/' + row['event_name'] + '_extracted.p'
    dat = root+'/data/timeseries/aggregated/' + row['incident_name'] + '_raw.parquet'
    
    df = pd.read_parquet(dat).iloc[row['start']:row['end']]
    samples = pickle.load(open(sample_loc,'rb'))
    
    x= np.arange(df.shape[0])*freq
    y = df['total_tweets'].values
    
    mu = np.mean(samples['y_hat'],axis=0)
    ci = np.percentile(samples['y_hat'],q=[5.5,94.5],axis=0)
    
    if cumulative:
        y=np.cumsum(y)
        mu = np.median(np.cumsum(samples['y_hat'],axis=1),axis=0)

        ci = np.percentile(np.cumsum(samples['y_hat'],axis=1)
                           ,q=[5.5,94.5],axis=0)
        
    plt.plot(x,y ,color='k')
    plt.plot(x,mu,ls='--',color='k')
    plt.fill_between(x, ci[0,:], ci[1,:],alpha=.3,color='k')
    
    
    plt.ylabel('Tweets per %s min.' % str(freq))
    if cumulative:
        plt.ylabel('Cumulative engagement \n(millions)')
    plt.xlabel('Time (min.)')
    plt.xlim(0,mu.size*freq-5)

def plot_posterior_and_save(row,root='.', keep=True,freq=5):
    file_output = root + '/output/figures/SI/posterior_predictive/' + row['event_name'] + '_pp.png'
    if row['included']==True:
        if keep and os.path.isfile(file_output):
            pass
        else:
            plt.subplot(211)
            samples = plot_posterior(row,cumulative=False, freq=5)
            plt.subplot(212)
            samples = plot_posterior(row,cumulative=True,freq=5)
            plt.suptitle(row['event_name'])
            plt.tight_layout()
            plt.savefig(file_output,dpi=400)
            plt.close()

def SI_Posterior(included, root='.'):
    for start in range(6):
        fig = plt.figure(figsize=(25.5,33))
        gs0 = gridspec.GridSpec(8,5, figure=fig)

        for idx in range(40):
            event = start*40 + idx

            if event >= included.shape[0]:
                break


            gs00 = gridspec.GridSpecFromSubplotSpec(2, 1, subplot_spec=gs0[idx])

            ax1 = fig.add_subplot(gs00[0, 0])
            plt.title(included.iloc[event]['event_name'])
            plot_posterior(included.iloc[event],cumulative=False)
            plt.xlabel('')
            plt.xticks([], [])
            ax2 = fig.add_subplot(gs00[1, 0])
            plot_posterior(included.iloc[event])

        plt.tight_layout()
        plt.savefig(root + '/output/figures/SI/SI_Fits_' + str(start*40)+'.png',dpi=300)
        plt.savefig(root + '/output/figures/SI/SI_Fits_' + str(start*40)+'.pdf',format='pdf')

        plt.close()
        
        
def add_sim_line(sim_row,scale=1e6,root='.'):
    vals = pickle.load(open(root + '/output/simulations/' + sim_row['name'] +'.p', 'rb'))
    keys = [key for key in vals.keys()]
    one_output = vals[keys[0]]

    interp_size = 20
    one_output = vals[keys[0]]
    out = np.zeros((one_output.shape[0], interp_size))

    for key in keys:
        one_output = vals[key]
        cumulative_scaled = np.apply_along_axis(interp,arr=np.cumsum(one_output,axis=1),axis=1)
        out+= cumulative_scaled

    mu = np.median(out,axis=0)/scale
    ci = np.percentile(out,axis=0, q=[5.5,94.5])/scale
    xvals = np.linspace(0,1,interp_size)
    plt.plot(xvals, mu,color=sim_row['color'])
    plt.fill_between(xvals, ci[0], ci[1],alpha=.4,color=sim_row['color'], label=sim_row['name'])
    
    return out

def plot_sims(order, sim_df, legend_title, legend_column):
    for idx in order:
        _ = add_sim_line(sim_df.iloc[idx])

    labels = sim_df.iloc[order][legend_column].values.astype('str').tolist()
    labels[0] = 'Base.'
    legend = plt.legend(labels=labels,title=legend_title,loc=2,prop={'size': 8})
    legend.get_title().set_fontsize('10')
    plt.ylim(0,6)
    plt.xlim(0,1)
    plt.xlabel('Time (normalized)')
    plt.ylabel('Cumulative engagement')
    
def plot_figure_1(row, included,pal,root='.'):
    fig, axs = plt.subplots(2,2,figsize=(8,8))
    axs = axs.flat

    for n, ax in enumerate(axs):
        ax.text(-0.1, 1.1, string.ascii_uppercase[n], transform=ax.transAxes, 
                size=20, weight='bold')

    ts = pd.read_parquet(row['data_loc'])[row['start']-20:row['end']+20]
    plt.sca(axs[0])
    y = ts['total_tweets'].values
    x = np.arange(y.shape[0])*5
    plt.plot(x,y,color='k')

    plt.xlim(0,np.max(x))
    start = row['start']
    start = 20*5
    end = (x.shape[0]-20)*5
    plt.plot([start,start],
              [0, np.max(y)*1.5],color='k',ls='--')
    plt.plot([end,end],
              [0, np.max(y)*1.5],color='k',ls='--')
    plt.ylim(0, np.max(y)*1.3)
    plt.ylabel('Tweets per 5 min.')
    plt.xlabel('Time (min.)')
    plt.xlim(-5,)

    plt.sca(axs[1])
    from src.figures import plot_posterior
    plot_posterior(row,cumulative=False)
    plt.xlim(-5,)


    plt.sca(axs[2])
    from src.figures import plot_posterior
    plot_posterior(row,cumulative=True)
    plt.xlim(-5,)


    plt.sca(axs[3])
    plt.ylabel('Cumulative engagement')



    ##Run single event simulations
    agg_df = pd.read_parquet(row['data_loc'])[row['start']:row['end']]
    follower_distribution = [np.array(item) for item in agg_df['follower_distribution'].values]
    y = agg_df['total_tweets']
    sample_loc = root+'/output/posteriors/' + row['event_name'] + '_extracted.p'
    samples = pickle.load(open(sample_loc,'rb'))

    baseline = []
    for idx in range(100):
        chain = np.random.choice(4000)
        out = simulate(samples,follower_distribution, y, chain)
        baseline.append(out)

    nudge = []
    for idx in range(100):
        chain = np.random.choice(4000)
        out = simulate(samples,follower_distribution, y, chain,
                      nudge=.9)
        nudge.append(out)

    vcb = []
    for idx in range(100):
        chain = np.random.choice(4000)
        out = simulate(samples,follower_distribution, y, chain,
                      vcb_value=.9, p_decay=1,decay_start=60)
        vcb.append(out)

    removal = []
    for idx in range(100):
        chain = np.random.choice(4000)
        out = simulate(samples,follower_distribution, y, chain,
                       p_decay=1, p_remove=1,decay_start=120,
                       stop_at=120)
        removal.append(out)  

    agg_df_ban = pd.read_parquet(row['verified_loc'])[row['start']:row['end']]
    follower_distribution_ban = [np.array(item) for item in agg_df_ban['follower_distribution'].values]
    y = agg_df_ban['total_tweets']

    ban = []
    for idx in range(100):
        chain = np.random.choice(4000)
        out = simulate(samples,follower_distribution_ban, y, chain)
        ban.append(out)



    get_cumulative = lambda x: np.median(np.cumsum(np.array(x).T,axis=0),
             axis=1)
    x = np.arange(get_cumulative(baseline).shape[0])*5

    plt.plot(get_cumulative(baseline),
            color='grey',lw=3,label='Baseline')
    plt.plot(get_cumulative(removal),
            color=pal[0],lw=3,label='Removal')
    plt.plot(get_cumulative(vcb),
            color=pal[-3],lw=3,label='VCB')
    plt.plot(get_cumulative(nudge),
            color=pal[2],lw=3,label='10% Nudge')
    plt.plot(get_cumulative(ban),
            color=pal[1],lw=3,label='Verified')

    legend = plt.legend(title='Condition',
                        loc=2,prop={'size': 8})
    legend.get_title().set_fontsize('10')

    plt.ylabel('Cumulative engagement')
    plt.xlabel('Time (min.)')
    plt.xlim(0,x.size)
    plt.tight_layout()